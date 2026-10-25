"""Run the mini-G4 circuits (data/MINI, from mini_g4.py) through Pauli-path on BlueQubit.

Same settings as our G4 runs, so we can see how Pauli-path behaves on a 2D Haar grid
whose exact answers are known (results/MINI/exact.json).

  python mini_pp.py --threshold 1e-4 --qubits 4,12           # probe a threshold on 2 qubits
  python mini_pp.py --threshold 5e-5                          # all qubits -> results/MINI/pp_lvl3_5e-05.json
  python score.py MINI --ref exact

Uploaded circuits, not hackathon IDs. pauli-path.gpu costs $0.20 per job; refused jobs are free.
"""
import argparse
import time

import bluequbit
from bluequbit.exceptions import BQJobNotCompleteError
from qiskit import qasm2

from common import DATA, load_cache, save_cache, z_on


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--qubits", help="e.g. 4,12 (default: all)")
    ap.add_argument("--device", default="pauli-path.gpu")
    ap.add_argument("--tag")
    ap.add_argument("--budget", type=float, default=1.0, help="stop once actual charges pass this")
    a = ap.parse_args()
    tag = a.tag or f"pp_lvl{a.level}_{a.threshold:g}"

    files = sorted((DATA / "MINI").glob("mini_*.qasm"), key=lambda p: int(p.stem.split("_")[1]))
    n = len(files)
    qubits = [int(x) for x in a.qubits.split(",")] if a.qubits else range(n)
    options = {"pauli_path_truncation_threshold": a.threshold,
               "pauli_path_circuit_transpilation_level": a.level}

    bq = bluequbit.init(execution_mode="cloud")
    cache = load_cache("MINI", tag)
    cache["meta"] = {"device": a.device, "options": options, "n": n}
    for q in qubits:
        key = f"MINI_{q}"
        if key in cache["values"]:
            continue
        if cache.get("cost", 0.0) > a.budget:
            print(f"budget ${a.budget:.2f} reached (spent ${cache['cost']:.2f}); stopping")
            break
        qc = qasm2.load(str(DATA / "MINI" / f"mini_{q}.qasm"))
        while True:
            try:
                job = bq.run(qc, device=a.device, pauli_sum=[(z_on(q, n), 1.0)],
                             options=options, job_name=f"MINI_{q}_{tag}")
                break
            except BQJobNotCompleteError as e:
                # the hackathon allows 1 GPU job at a time per account
                if "HACKATHON_PARALLEL_JOBS_LIMIT" in str(e) or "HACKATHON_GPU_QUOTA_COOLDOWN" in str(e):
                    time.sleep(20)
                    continue
                if "FAILED_VALIDATION" in str(e):
                    job = None
                    break
                raise
        if job is None:
            print(f"  {key}: threshold {a.threshold:g} rejected")
            continue
        cache["values"][key] = float(job.expectation_value)
        cache["cost"] = cache.get("cost", 0.0) + (job.cost or 0.0)
        save_cache("MINI", tag, cache)
        print(f"  {key:>8} = {job.expectation_value:+.6f}  [{job.run_time_ms}ms ${job.cost or 0:.2f}, "
              f"total ${cache['cost']:.2f}]", flush=True)


if __name__ == "__main__":
    main()
