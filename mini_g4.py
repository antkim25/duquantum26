"""A small, exactly solvable stand-in for G4, to test G4 methods against known answers.

G4 is a 2D grid of Haar-random two-qubit gates (compiled to u3 + cz) with the butterfly
X on corner qubit 0. This builds the same thing on a ROWS x COLS grid:
    U, X(q0), U^dag, Z(qk), U, X(q0), U^dag   applied to |0...0>, then <Z_k>
one circuit per k, like Duke_G4_k. The exact answers come from a local statevector.

  python mini_g4.py --layers 12                 # build + exact values -> results/MINI/exact.json
  python mini_g4.py --layers 12 --rows 4 --cols 5 --seed 1

Circuits are saved to data/MINI/mini_<k>.qasm (OpenQASM 2, u3/cz/x/z, like the samples).
"""
import argparse
import json
import time

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.quantum_info import SparsePauliOp, random_unitary
from qiskit_aer import AerSimulator

from common import DATA, RESULTS, z_on


def grid_layers(rows, cols):
    """The 4 nearest-neighbour edge sets of a grid, cycled like G3/G4 (qubit = row*cols + col)."""
    q = lambda r, c: r * cols + c
    h0 = [(q(r, c), q(r, c + 1)) for r in range(rows) for c in range(0, cols - 1, 2)]
    h1 = [(q(r, c), q(r, c + 1)) for r in range(rows) for c in range(1, cols - 1, 2)]
    v0 = [(q(r, c), q(r + 1, c)) for r in range(0, rows - 1, 2) for c in range(cols)]
    v1 = [(q(r, c), q(r + 1, c)) for r in range(1, rows - 1, 2) for c in range(cols)]
    return [h0, v0, h1, v1]


def build_u(rows, cols, layers, seed):
    n = rows * cols
    rng = np.random.default_rng(seed)
    u = QuantumCircuit(n)
    sets = grid_layers(rows, cols)
    for layer in range(layers):
        for a, b in sets[layer % 4]:
            u.unitary(random_unitary(4, seed=int(rng.integers(2**31))), [a, b])
    return transpile(u, basis_gates=["u3", "cz"], optimization_level=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--layers", type=int, default=12, help="two-qubit layers in U (G4 has 16 on 6x6)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    n = a.rows * a.cols

    u = build_u(a.rows, a.cols, a.layers, a.seed)
    udg = u.inverse()
    folder = DATA / "MINI"
    folder.mkdir(parents=True, exist_ok=True)
    # the first U, X(q0), U^dag is the same for every k, so compute that state once
    w = QuantumCircuit(n)
    w.compose(u, inplace=True); w.x(0); w.compose(udg, inplace=True)
    sim = AerSimulator(method="statevector")
    first = w.copy(); first.save_statevector()
    a_state = sim.run(transpile(first, sim)).result().get_statevector()
    values = {}
    t0 = time.time()
    for k in range(n):
        full = QuantumCircuit(n)
        full.compose(w, inplace=True); full.z(k); full.compose(w, inplace=True)
        full = transpile(full, basis_gates=["u3", "cz", "x", "z"], optimization_level=0)
        (folder / f"mini_{k}.qasm").write_text(qasm2.dumps(full))
        rest = QuantumCircuit(n)
        rest.set_statevector(a_state); rest.z(k); rest.compose(w, inplace=True); rest.save_statevector()
        sv = sim.run(transpile(rest, sim)).result().get_statevector()
        values[f"MINI_{k}"] = float(np.real(sv.expectation_value(SparsePauliOp(z_on(k, n)))))
        print(f"  q{k:<3} exact = {values[f'MINI_{k}']:+.4f}   ({time.time() - t0:.0f}s)", flush=True)

    out = RESULTS / "MINI" / "exact.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {"rows": a.rows, "cols": a.cols, "layers": a.layers, "seed": a.seed, "n": n,
            "cz_in_U": u.count_ops().get("cz", 0)}
    out.write_text(json.dumps({"meta": meta, "values": values}, indent=1))
    v = np.array(list(values.values()))
    print(f"\nwrote {out}  | CZ per U: {meta['cz_in_U']} | "
          f"|v|<0.1: {(abs(v) < 0.1).sum()}/{n}, max |v| = {abs(v).max():.3f}")


if __name__ == "__main__":
    main()
