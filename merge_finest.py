"""Merge Pauli-path runs, taking for each qubit the run that used the smallest threshold.

  python merge_finest.py G4 t_lvl3_2e5_log g4_finest_lvl3 g4_fine_t2 <avi's tag> --name G4_lvl3_finest

A run's threshold per qubit comes from its "threshold" field (pp_finest.py), else from
meta.options.pauli_path_truncation_threshold (run_circuit.py). On a tie, the earlier tag wins.
Writes submissions/<name>.csv and prints where each qubit came from.
"""
import argparse

from common import cid, load_cache, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--name")
    a = ap.parse_args()

    runs = [(t, load_cache(a.circuit, t)) for t in a.tags]
    for t, r in runs:
        if not r["values"]:
            raise SystemExit(f"run '{t}' has no values (wrong tag?)")
    n = max(r["meta"].get("n", 0) for _, r in runs)

    values = []
    for q in range(n):
        key = cid(a.circuit, q)
        best = None
        for tag, r in runs:
            if key not in r["values"]:
                continue
            th = r.get("threshold", {}).get(key)
            if th is None:
                th = r["meta"].get("options", {}).get("pauli_path_truncation_threshold")
            if th is None:
                raise SystemExit(f"run '{tag}' has no threshold for {key}")
            if best is None or th < best[0]:
                best = (th, tag, r["values"][key])
        if best is None:
            raise SystemExit(f"qubit {q} is missing from every run")
        values.append(best[2])
        print(f"  q{q:<3} {best[2]:+.6f}  at {best[0]:g}  from {best[1]}")

    print("wrote", write_csv(a.circuit, values, a.name or f"{a.circuit}_finest_merged"))


if __name__ == "__main__":
    main()
