"""Score every cached run of a sample circuit against a reference, the way the grader does.

  python score.py S1                  # all tags vs exact_local
  python score.py S1 --ref cpu        # vs a BlueQubit exact cpu run
  python score.py G1                  # no reference: shows how runs agree with each other

Score = corr(estimate, exact)^2, with corr<0 counting as 0. Scale and offset don't matter.
"""
import argparse
import json

import numpy as np

from common import RESULTS


def corr2(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    if a.std() == 0 or b.std() == 0:
        return 0.0
    r = np.corrcoef(a, b)[0, 1]
    return float(r * r) if r > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("--ref", default="exact_local")
    a = ap.parse_args()

    runs = {p.stem: json.loads(p.read_text())["values"]
            for p in sorted((RESULTS / a.circuit).glob("*.json"))}
    if not runs:
        raise SystemExit(f"no results for {a.circuit}")

    refs = [a.ref] if a.ref in runs else list(runs)
    if a.ref not in runs:
        print(f"(no '{a.ref}' run, so comparing all runs pairwise)")
    for ref in refs:
        print(f"\nreference: {ref}")
        for tag, vals in runs.items():
            if tag == ref:
                continue
            common = sorted(set(vals) & set(runs[ref]))
            if len(common) < 2:
                continue
            s = corr2([vals[k] for k in common], [runs[ref][k] for k in common])
            print(f"  {tag:<32} corr^2 = {s:.4f}   ({len(common)} qubits)")


if __name__ == "__main__":
    main()
