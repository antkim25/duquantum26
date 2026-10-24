# DuQuantum 2026: BlueQubit OTOC challenge

Estimate <Z_q> after each hidden circuit `Duke_<C>_<q>` and get the highest Pearson corr² against the exact values.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BLUEQUBIT_API_TOKEN=...   # top bar on bluequbit.io → "See API token"
```

## Workflow
```bash
python info.py                                    # sizes of all circuits (free)

# samples: exact reference + method tuning
#   unzip the sample QASM into data/S1/ first
python exact_local.py S1                          # exact, local
python run_circuit.py S1 --device mps.cpu --chi 16
python run_circuit.py S1 --device pauli-path --threshold 1e-3
python score.py S1                                # corr² of each method vs exact

# graded circuits: test cost on a few qubits, then run all of them
python run_circuit.py G1 --device mps.cpu --chi 64 --limit 3
python run_circuit.py G1 --device mps.cpu --chi 64
```
Each run is cached in `results/<C>/<tag>.json`, so rerunning a command picks up where it stopped.
Finished runs write `submissions/<C>_<tag>.csv`, ready to upload.
