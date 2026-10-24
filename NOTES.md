# BlueQubit OTOC challenge: working notes

Write down each decision and why as you go. This becomes the presentation.

## Circuit sizes (from `python info.py`)
| circuit | qubits | 2q depth | notes |
|---|---|---|---|
| S1 | 4 | 48 | exact locally |
| S2 | 16 | 144 | exact locally |
| S3 | 30 | 128 | 17 GB statevector: too big for laptop, try BlueQubit cpu |
| G1 | 30 | 384 | same size as S3: try BlueQubit exact |
| G2 | 36 | 216 | ~1 TB statevector: must approximate |
| G3 | 36 | 192 | must approximate |
| G4 | 38 | 192 | ~4 TB statevector: must approximate |

BlueQubit limits (from SDK): pauli-path max 6000 two-qubit gates (G1 has 5568), max 10 queued cpu jobs.

## Circuit structure (found by reading S1 QASM, verified numerically)
Every file in a circuit is identical except ONE line: the `z q[k]` in the middle.
File for ID k = `U, X(q0), U†, Z(qk), U, X(q0), U†` applied to |0...0>, then measure Z on qk.

With W = U† X0 U (the "butterfly" X on qubit 0, evolved in time) the answer is
    <Z_k> = <0| (Z_k W)^4 |0>        (checked: matches exact values on all 4 S1 qubits)
This is a 4-point out-of-time-order correlator (OTOC) between the butterfly (X on q0) and the measured qubit k.

Intuition: if the poke at q0 never reaches qubit k, W commutes with Z_k, so (Z_k W)^4 = 1 and the value is +1.
The more the poke has scrambled into qubit k, the further the value falls from 1.
So the per-qubit pattern = "how strongly did information from q0 spread to qubit k".

## Method experiments on samples (corr² vs exact)
| circuit | method/settings | corr² | cost/time | notes |
|---|---|---|---|---|

## Submissions
| circuit | file | method | score |
|---|---|---|---|
| S1 | S1_exact_local.csv | exact statevector (Qiskit, local); matches BlueQubit cpu (corr²=1) | 100/100 (12:31, penalty 1.03h) |

## What I learned / dead ends
