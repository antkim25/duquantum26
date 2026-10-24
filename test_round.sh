#!/bin/bash
# Test round: one qubit per setting, to measure runtime and actual cost before full G2-G4 runs.
# Pauli-path jobs hold ~$25 of balance while running, so they go one at a time (--batch 1).
cd "$(dirname "$0")"
mkdir -p logs
export PYTHONUNBUFFERED=1

python run_circuit.py G3 --device pauli-path --threshold 1e-4 --qubits 14 --batch 1 --budget 1 \
    > logs/test_G3_pp1e-4.log 2>&1 &
sleep 30  # let the pauli-path hold land first so the MPS job cannot crowd it out
python run_circuit.py G2 --device mps.cpu --chi 128 --qubits 8 --batch 1 --budget 1 \
    > logs/test_G2_chi128.log 2>&1 &
wait %1
echo "G3 lvl2 done: $(date)"

python run_circuit.py G4 --device pauli-path --threshold 1e-4 --qubits 14 --batch 1 --budget 1 \
    > logs/test_G4_pp1e-4.log 2>&1
echo "G4 done: $(date)"

python run_circuit.py G3 --device pauli-path --threshold 1e-4 --level 3 --qubits 14 --batch 1 --budget 1 \
    > logs/test_G3_pp1e-4_lvl3.log 2>&1
echo "G3 lvl3 done: $(date)"
wait
echo "all done: $(date)"
