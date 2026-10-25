# DuQuantum 2026: BlueQubit OTOC challenge

Each circuit `Duke_<C>_<q>` runs U, X (butterfly), U†, Z_q, U, X, U†: an out-of-time-order correlator.
We estimate ⟨Z_q⟩ for every qubit q; a circuit's score is Pearson corr² against the exact values × its points.

## Results: 2,198 / 3,000

| Circuit | Qubits | Layout | Method | Score |
|---|---|---|---|---|
| S1 | 4 | – | exact statevector, local | 100 / 100 |
| S2 | 16 | 1D chain | exact statevector, local | 100 / 100 |
| S3 | 30 | 5×6 grid | exact statevector, BlueQubit CPU | 100 / 100 |
| G1 | 30 | 1D chain | exact statevector, BlueQubit CPU | 300 / 300 |
| G2 | 36 | 1D chain | Pauli-path GPU, transpilation level 3, finest accepted threshold per qubit | 591 / 600 |
| G3 | 36 | 6×6 grid | Pauli-path GPU, transpilation level 1, finest accepted threshold per qubit | 800 / 800 |
| G4 | 38 | 2D | Pauli-path GPU, transpilation level 3, finest accepted threshold per qubit | 207 / 1000 |

Submitted files (in `submissions/`): `S1_exact_local.csv`, `S2_exact_local.csv`, `S3_cpu.csv`, `G1_cpu.csv`,
`G2_g2_finest_lvl3.csv`, `G3_ppgpu_lvl1.csv`, `G4_lvl3_finest.csv`.

## What we learned

- **Exact first, then use it as ground truth.** Up to 30 qubits fit in a statevector, so the samples gave us exact answers to test every approximate method against before spending credits on hidden circuits.
- **MPS works on chains, not on grids.** On G2 (a chain), MPS scores rose with bond dimension (χ = 64 → 128 → 256 gave 426 → 497 → 547) but never settled. On G4 (2D), MPS χ = 64 scored 0. To see why, we ran MPS χ = 512 on S3, a grid with known answers: some qubits matched, but others were far off (q27: +0.10 vs exact +0.96). Flattening a 2D grid into a 1D chain needs far more bond dimension than we could afford.
- **Pauli-path: the threshold is not the only knob.** Pauli-path drops Pauli terms whose weight falls below a truncation threshold. Coarse thresholds collapsed everything to ≈ 0. The server rejects thresholds it predicts would run out of memory, and *which* thresholds it accepts depends on the circuit transpilation level (0–3). `pp_finest.py` tries thresholds finest-first (1e-5, 1.5e-5, 2e-5, 3e-5, 5e-5, 1e-4) per qubit and keeps the first one accepted. That took G3 from 0 to 800/800 and G2 from 547 to 591.
- **Error is not monotonic in threshold** (consistent with the BlueQubit benchmarking paper, arXiv 2607.09882), so a finer setting is not automatically better. We validated settings on S2/S3 against exact values before trusting them.
- **G4 limits.** At level 3, Pauli-path recovers the strongest signals (q36/37 ≈ +0.15, q28/29 ≈ +0.13, q22 ≈ +0.08), but the rest come out ≈ 0. The circuits use Haar-random blocks designed to resist Pauli-path, and the reference answers came from an exact 38-qubit statevector. Closing this gap needs a different method.

Full lab notebook (every run, cost, and dead end): [`NOTES.md`](NOTES.md).

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BLUEQUBIT_API_TOKEN=...   # top bar on bluequbit.io → "See API token"
```

## Reproduce
```bash
python info.py                                   # sizes of all circuits (free)

# exact answers (unzip the sample QASM into data/<C>/ first)
python exact_local.py S1
python run_circuit.py S3 --device cpu            # 30 qubits: BlueQubit CPU statevector
python run_circuit.py G1 --device cpu

# MPS (tensor network); test a few qubits first
python run_circuit.py G2 --device mps.cpu --chi 256 --limit 3
python run_circuit.py G2 --device mps.cpu --chi 256

# Pauli-path at the finest accepted threshold per qubit
python pp_finest.py G3 --level 1 --budget 10
python pp_finest.py G2 --level 3 --budget 8 --tag g2_finest_lvl3
python pp_finest.py G4 --level 3 --budget 8 --tag g4_finest_lvl3

# combine runs split across teammates, keeping the finest threshold per qubit
python merge_finest.py G4 t_lvl3_2e5_log g4_finest_lvl3 g4_fine_t2 g4_fine_t1_log --name G4_lvl3_finest

python score.py S2                               # corr² of each method vs exact (samples only)
```

Every run is cached in `results/<C>/<tag>.json` (values, threshold used, cost per job), so rerunning a command
resumes where it stopped and never pays twice. A finished run writes `submissions/<C>_<tag>.csv`.
`--budget` caps the dollars a run may spend; rejected jobs (threshold too fine) are free.

## Files

| File | Purpose |
|---|---|
| `run_circuit.py` | Run all qubits of a circuit on any BlueQubit device; resumable, budget-capped |
| `pp_finest.py` | Pauli-path with the finest server-accepted threshold per qubit |
| `merge_finest.py`, `merge.py` | Combine partial runs into one submission |
| `exact_local.py` | Exact statevector locally (S1, S2) |
| `score.py` | corr² of each method against exact values |
| `info.py` | Circuit sizes and structure |
| `common.py` | Shared cache and CSV helpers |
| `results/`, `submissions/`, `logs/` | Raw results, uploaded CSVs, run logs |
