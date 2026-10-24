"""Build one submission from several runs: for each qubit, take the first run (in the order given) that has it.

  python merge.py G2 mps.cpu_chi128 mps.cpu_chi64
  python merge.py G2 mps.cpu_chi256 mps.cpu_chi128 mps.cpu_chi64 --name G2_mps_best

Writes submissions/<name>.csv (default <circuit>_merged) and prints which run each qubit came from.
"""
import argparse

from common import cid, load_cache, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("tags", nargs="+", help="run tags, highest priority first")
    ap.add_argument("--name")
    a = ap.parse_args()

    runs = [(t, load_cache(a.circuit, t)) for t in a.tags]
    n = max(r["meta"].get("n", 0) for _, r in runs)
    values, source = [], []
    for q in range(n):
        for tag, r in runs:
            if cid(a.circuit, q) in r["values"]:
                values.append(r["values"][cid(a.circuit, q)])
                source.append(tag)
                break
        else:
            raise SystemExit(f"qubit {q} is missing from every run")

    for tag in a.tags:
        qs = [q for q in range(n) if source[q] == tag]
        print(f"  {tag:<24} {len(qs):>2} qubits: {qs}")
    print("wrote", write_csv(a.circuit, values, a.name or f"{a.circuit}_merged"))


if __name__ == "__main__":
    main()
