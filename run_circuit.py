"""Run every qubit ID of one circuit on BlueQubit, resumably.

Examples:
  python run_circuit.py S1 --device cpu
  python run_circuit.py G1 --device mps.cpu --chi 64 --limit 3      # cheap test first
  python run_circuit.py G2 --device pauli-path --threshold 1e-3
  python run_circuit.py G2 --device pauli-path --threshold 1e-3 --tag pp_1e-3_try2

Results go to results/<circuit>/<tag>.json. Rerunning the same command skips
finished IDs and picks up jobs that were still running when the script stopped.
When every qubit is done, it writes submissions/<circuit>_<tag>.csv.
"""
import argparse
import time

import bluequbit
from bluequbit.exceptions import BQJobNotCompleteError
from bluequbit.job_metadata_constants import JOB_NO_RESULT_TERMINAL_STATES

from common import cid, load_cache, save_cache, values_in_order, write_csv, z_on


RETRY_STATES = {"JOBS_LIMIT_EXCEEDED", "HACKATHON_PARALLEL_JOBS_LIMIT",
                "HACKATHON_GPU_QUOTA_COOLDOWN"}


def default_tag(a) -> str:
    tag = a.device
    if a.chi:
        tag += f"_chi{a.chi}"
    if a.threshold is not None:
        tag += f"_th{a.threshold:g}"
    if a.level is not None:
        tag += f"_lvl{a.level}"
    if a.weight is not None:
        tag += f"_w{a.weight}"
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", help="S1..S3 or G1..G4")
    ap.add_argument("--device", default="cpu",
                    choices=["cpu", "gpu", "mps.cpu", "mps.gpu", "pauli-path", "pauli-path.gpu"])
    ap.add_argument("--chi", type=int, help="mps_bond_dimension")
    ap.add_argument("--threshold", type=float, help="pauli_path_truncation_threshold (min 1e-5)")
    ap.add_argument("--level", type=int, help="pauli_path_circuit_transpilation_level 0-3")
    ap.add_argument("--weight", type=int, help="pauli_path_weight_cutoff (pauli-path.gpu only; not in the docs)")
    ap.add_argument("--force-run", action="store_true", help="mps only: bypass server-side runtime limits")
    ap.add_argument("--shots", type=int, help="samples to draw (server default 1024 for mps; we only need the expectation)")
    ap.add_argument("--tag", help="name for this run (default built from settings)")
    ap.add_argument("--qubits", help="only these qubits, e.g. 0,5,9")
    ap.add_argument("--limit", type=int, help="only the first N qubits (for cost tests)")
    ap.add_argument("--batch", type=int, default=5, help="jobs in flight at once (hackathon limit: 5 running per user)")
    ap.add_argument("--wait-funds", action="store_true",
                    help="on NOT_ENOUGH_FUNDS at submit, wait and retry (another run is holding the balance)")
    ap.add_argument("--budget", type=float, default=1.0,
                    help="stop submitting once this run's ACTUAL charges pass this many dollars")
    a = ap.parse_args()

    bq = bluequbit.init(execution_mode="cloud")  # hidden circuits only run in the cloud; Hybrid machines default to local
    first = cid(a.circuit, 0)
    info = bq.get_circuit_info(first)  # free
    n = info.num_qubits
    print(f"{a.circuit}: {n} qubits | info: {info}")

    options = {}
    if a.chi:
        options["mps_bond_dimension"] = a.chi
    if a.threshold is not None:
        options["pauli_path_truncation_threshold"] = a.threshold
    if a.level is not None:
        options["pauli_path_circuit_transpilation_level"] = a.level
    if a.weight is not None:
        options["pauli_path_weight_cutoff"] = a.weight

    tag = a.tag or default_tag(a)
    cache = load_cache(a.circuit, tag)
    cache["meta"] = {"device": a.device, "options": options, "n": n}

    # adopt jobs this run already submitted (matched by job name) that the cache lost,
    # e.g. after a crash, so they aren't paid for twice
    prefix, suffix = f"{a.circuit}_", f"_{tag}"
    for job in bq.search():
        name = job.job_name or ""
        if not (name.startswith(prefix) and name.endswith(suffix)):
            continue
        key = cid(a.circuit, int(name[len(prefix):-len(suffix)]))
        if key in cache["values"] or key in cache["pending"]:
            continue
        if job.ok:
            cache["values"][key] = float(job.expectation_value)
            print(f"  recovered {key} = {job.expectation_value:+.6f} from job {job.job_id}")
        elif job.run_status not in JOB_NO_RESULT_TERMINAL_STATES:
            cache["pending"][key] = job.job_id
            print(f"  re-attached to running job for {key}")
    save_cache(a.circuit, tag, cache)

    qubits = range(n)
    if a.qubits:
        qubits = [int(x) for x in a.qubits.split(",")]
    elif a.limit:
        qubits = range(min(a.limit, n))
    todo = [q for q in qubits
            if cid(a.circuit, q) not in cache["values"]
            and cid(a.circuit, q) not in cache["pending"]]
    print(f"tag={tag}  done={len(cache['values'])}  pending={len(cache['pending'])}  new={len(todo)}")

    t0 = time.time()
    while todo or cache["pending"]:
        # top up in-flight jobs
        if todo and cache.get("cost", 0.0) > a.budget:
            print(f"budget ${a.budget:.2f} reached (spent ${cache['cost']:.2f}); "
                  f"not submitting {len(todo)} more. Rerun with a higher --budget to continue.")
            todo = []
        slots_full = False
        while todo and len(cache["pending"]) < a.batch:
            q = todo.pop(0)
            try:
                job = bq.run(cid(a.circuit, q), device=a.device, asynchronous=True,
                             pauli_sum=[(z_on(q, n), 1.0)], options=options or None,
                             job_name=f"{a.circuit}_{q}_{tag}", force_run=a.force_run,
                             shots=a.shots)
            except BQJobNotCompleteError as e:
                # the hackathon rejects a submit outright when 5 jobs are already running
                # (including jobs from other scripts), so wait for a slot and try again
                # with --wait-funds, a refusal because another run is holding the balance also waits
                funds = a.wait_funds and "NOT_ENOUGH_FUNDS" in str(e)
                if not funds and not any(s in str(e) for s in RETRY_STATES):
                    raise
                todo.insert(0, q)
<<<<<<< Updated upstream
                if funds:
                    time.sleep(60)  # each refused submit is a job; don't burn the daily job cap
=======
                slots_full = True
>>>>>>> Stashed changes
                break
            cache["pending"][cid(a.circuit, q)] = job.job_id
            save_cache(a.circuit, tag, cache)

        # collect finished jobs
        ids = list(cache["pending"].values())
        jobs = bq.get(ids) if ids else []
        for job in jobs if isinstance(jobs, list) else [jobs]:
            key = next(k for k, v in cache["pending"].items() if v == job.job_id)
            if job.ok or job.run_status in JOB_NO_RESULT_TERMINAL_STATES:
                # per-job record for NOTES.md: how long it ran, what it cost, how it ended
                cache.setdefault("metrics", {})[key] = {
                    "job_id": job.job_id, "status": job.run_status,
                    "run_time_ms": job.run_time_ms, "queue_time_ms": job.queue_time_ms,
                    "cost": job.cost, "error": job.error_message}
            if job.ok:
                cache["values"][key] = float(job.expectation_value)
                del cache["pending"][key]
                # the "estimated cost" printed at submit is a worst case; this is the real charge
                cache["cost"] = cache.get("cost", 0.0) + (job.cost or 0.0)
                print(f"  {key:>14} = {job.expectation_value:+.6f}   "
                      f"[{len(cache['values'])}/{n}, {time.time() - t0:.0f}s, "
                      f"job {job.run_time_ms}ms ${job.cost or 0:.2f}, run total ${cache['cost']:.2f}]")
            elif job.run_status in RETRY_STATES or (
                    a.wait_funds and job.run_status == "NOT_ENOUGH_FUNDS"):
                del cache["pending"][key]
                todo.append(int(key.rsplit("_", 1)[1]))
                print(f"  {key}: {job.run_status}, will retry")
                time.sleep(10)
            elif job.run_status in JOB_NO_RESULT_TERMINAL_STATES:
                del cache["pending"][key]
                print(f"  {key}: {job.run_status} {job.error_message}")
                if job.run_status == "NOT_ENOUGH_FUNDS":
                    raise SystemExit("out of credits")
        save_cache(a.circuit, tag, cache)
        if slots_full:
            time.sleep(20)  # all 5 account slots busy (maybe other scripts): don't hammer the server
        elif cache["pending"]:
            time.sleep(3)

    if len(cache["values"]) == n:
        out = write_csv(a.circuit, values_in_order(a.circuit, tag, n), f"{a.circuit}_{tag}")
        print(f"wrote {out}   (actual cost of this run: ${cache.get('cost', 0):.2f})")
    else:
        print(f"{len(cache['values'])}/{n} done; no CSV yet")


if __name__ == "__main__":
    main()
