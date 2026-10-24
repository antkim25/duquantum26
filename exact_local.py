"""Exact <Z_q> for the open sample circuits, simulated on this machine.

Unzip a sample's QASM files into data/<circuit>/ (Duke_S1_0.qasm, ...), then:
  python exact_local.py S1

Writes results/S1/exact_local.json, the reference that score.py compares
approximate methods against. Statevector memory is 16 * 2**n bytes:
n=26 is ~1 GB, n=30 is ~17 GB. For bigger samples use run_circuit.py --device cpu/gpu.
"""
import argparse
import time

from qiskit import qasm2
from qiskit.quantum_info import SparsePauliOp, Statevector

from common import DATA, cid, load_cache, save_cache, write_csv, values_in_order, z_on


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("--tag", default="exact_local")
    a = ap.parse_args()

    folder = DATA / a.circuit
    files = sorted(folder.glob(f"Duke_{a.circuit}_*.qasm"),
                   key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    if not files:
        raise SystemExit(f"no QASM files in {folder}")

    cache = load_cache(a.circuit, a.tag)
    n = None
    for path in files:
        q = int(path.stem.rsplit("_", 1)[1])
        key = cid(a.circuit, q)
        if key in cache["values"]:
            continue
        qc = qasm2.load(str(path))  # u3/cz/x/z are all in qelib1.inc
        n = qc.num_qubits
        t = time.time()
        # Qiskit is little-endian like BlueQubit: qubit 0 is the rightmost Pauli char
        val = Statevector(qc).expectation_value(SparsePauliOp(z_on(q, n))).real
        cache["values"][key] = float(val)
        cache["meta"] = {"device": "qiskit-statevector", "n": n}
        save_cache(a.circuit, a.tag, cache)
        print(f"  {key:>14} = {val:+.6f}  ({n}q, {qc.size()} gates, {time.time() - t:.1f}s)")

    n = cache["meta"]["n"]
    if len(cache["values"]) == n:
        print("wrote", write_csv(a.circuit, values_in_order(a.circuit, a.tag, n),
                                 f"{a.circuit}_{a.tag}"))


if __name__ == "__main__":
    main()
