"""Pauli-path at the finest threshold the server accepts, per qubit.

The server rejects thresholds it predicts would overflow memory (FAILED_VALIDATION),
and the limit differs per qubit. This tries thresholds finest-first and keeps the
first accepted one. Rejected jobs don't run.

  python pp_finest.py S3 --qubits 8,14
  python pp_finest.py G3 --qubits 14,8,20,0 --budget 2
  python pp_finest.py S3 --qubits 14 --level 3          # different transpilation level

Results go to results/<circuit>/ppgpu_finest.json, with the threshold used per qubit.
"""
import argparse
import time

import bluequbit
from bluequbit.exceptions import BQJobNotCompleteError

from common import cid, load_cache, save_cache, values_in_order, write_csv, z_on

LADDER = [1e-5, 1.5e-5, 2e-5, 3e-5, 5e-5, 1e-4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("--qubits", help="e.g. 0,5,9 (default: all)")
    ap.add_argument("--device", default="pauli-path.gpu")
    ap.add_argument("--level", type=int, help="pauli_path_circuit_transpilation_level 0-3 (server default 2)")
    ap.add_argument("--tag", help="default: ppgpu_finest, plus _lvl<N> when --level is given")
    ap.add_argument("--budget", type=float, default=1.0, help="stop once actual charges pass this")
    a = ap.parse_args()

    a.tag = a.tag or "ppgpu_finest" + (f"_lvl{a.level}" if a.level is not None else "")
    extra = {} if a.level is None else {"pauli_path_circuit_transpilation_level": a.level}

    bq = bluequbit.init(execution_mode="cloud")
    n = bq.get_circuit_info(cid(a.circuit, 0)).num_qubits
    cache = load_cache(a.circuit, a.tag)
    cache["meta"] = {"device": a.device, "n": n, "ladder": LADDER, "options": extra}
    cache.setdefault("threshold", {})
    qubits = [int(x) for x in a.qubits.split(",")] if a.qubits else range(n)

    for q in qubits:
        key = cid(a.circuit, q)
        if key in cache["values"]:
            continue
        if cache.get("cost", 0.0) > a.budget:
            print(f"budget ${a.budget:.2f} reached (spent ${cache['cost']:.2f}); stopping")
            break
        ladder = list(LADDER)
        while ladder:
            th = ladder[0]
            try:
                job = bq.run(key, device=a.device, pauli_sum=[(z_on(q, n), 1.0)],
                             options={"pauli_path_truncation_threshold": th, **extra},
                             job_name=f"{a.circuit}_{q}_{a.tag}")
            except BQJobNotCompleteError as e:
                if "FAILED_VALIDATION" in str(e):
                    print(f"  {key}: {th:g} rejected")
                    ladder.pop(0)
                    continue
                # the hackathon allows 1 GPU job at a time per account, so wait and retry
                if "HACKATHON_PARALLEL_JOBS_LIMIT" in str(e) or "HACKATHON_GPU_QUOTA_COOLDOWN" in str(e):
                    time.sleep(20)
                    continue
                raise
            cache["values"][key] = float(job.expectation_value)
            cache["threshold"][key] = th
            cache["cost"] = cache.get("cost", 0.0) + (job.cost or 0.0)
            save_cache(a.circuit, a.tag, cache)
            print(f"  {key:>14} = {job.expectation_value:+.6f}  at {th:g}  "
                  f"[{job.run_time_ms}ms ${job.cost or 0:.2f}, total ${cache['cost']:.2f}]")
            break
        else:
            print(f"  {key}: every threshold rejected")

    if len(cache["values"]) == n:
        print("wrote", write_csv(a.circuit, values_in_order(a.circuit, a.tag, n), f"{a.circuit}_{a.tag}"))


if __name__ == "__main__":
    main()
