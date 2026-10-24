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
| S2 | S2_exact_local.csv | exact statevector (local), matches BlueQubit cpu | 100/100 |
| S3 | S3_cpu.csv | exact statevector, BlueQubit cpu by ID | 100/100 |
| G1 | G1_cpu.csv | exact statevector, BlueQubit cpu by ID | 300/300 |
| S1 | S1_exact_local.csv | exact statevector (Qiskit, local); matches BlueQubit cpu (corr²=1) | 100/100 (12:31, penalty 1.03h) |

## What I learned / dead ends

## Layouts and butterfly qubits (from sample QASM)
- S1: 4 qubits in a line 0-1-2-3, butterfly X on q0
- S2: 16 qubits in a line 0-1-...-15, butterfly X on q0.
  Exact values: q12-15 = exactly +1 (poke never reached them), q10-11 ~ +0.6, q0-9 ~ 0 (fully scrambled).
  => clear light cone spreading ~11 sites down the chain.
- S3: 30 qubits on a 5x6 grid (q = 6*row + col, nearest-neighbour cz), butterfly X on q14 (row 2, col 2, near centre).
  The butterfly qubit is NOT always q0, so it must be found for each G circuit.

## Cost findings
- BlueQubit's "estimated cost" at submit is a worst case (pauli-path showed $25); actual charge so far $0.00 for every job.
- Exact cpu on 30 qubits works: S3 one qubit = ~50 s, $0.00. So S3 and G1 (30 qubits) can be done exactly.
- Pauli-path threshold 1e-2 on S2 gives exactly 0: truncation drops every term. Needs a much smaller threshold.
- Hackathon limit: max 5 jobs running at once per user (across all scripts). Runner now uses 5 and waits for a slot.
- Pauli-path on S2 qubit 10 (exact +0.58): th 1e-2 -> 0.000 (1 s), 1e-3 -> 0.000 (4 s), 1e-4 -> 0.005 (155 s), all $0.
  Hypothesis: the circuit is 4 copies of U (U X U† Z U X U†), so backward Pauli propagation through the
  whole thing makes huge numbers of terms; truncation cuts off the cancellations and the value collapses to ~0.
  => direct pauli-path on these circuits looks weak; need to confirm on more qubits.
- S3 exact on BlueQubit cpu: 30 jobs, ~45-50 s each, 5 in parallel, ~6 min total, $0.00. Values are messy on the grid
  (some strongly negative, e.g. -0.81): not a simple distance-from-butterfly pattern.
- G1 exact on BlueQubit cpu: 30 jobs, ~50-60 s each, ~9 min total, $0.00.
  Values: q0-19 ~ 0, then rising smoothly q20 +0.08 -> q29 +0.95. Looks like a 1D chain with the light cone
  ending around q20-q24 (similar to S2).

## G2-G4: exact is impossible
- BlueQubit cpu rejects > 34 qubits; gpu rejects 36 ("too high for GPU backend"). So G2 (36), G3 (36), G4 (38) must be approximated.
- MPS chi 64 on one G2 qubit: 56 s, $0.00 (estimate said $0.91 / 36 min).

## Approximations collapse toward 0, but keep some ordering
MPS chi 64 vs exact on 5 S3 qubits:
| qubit | exact | mps64 |
|---|---|---|
| 16 | -0.686 | -0.000 |
| 7 | -0.511 | +0.002 |
| 0 | +0.144 | +0.105 |
| 14 | +0.025 | -0.000 |
| 27 | +0.958 | +0.084 |
corr² = 0.53 on these 5. Values are squashed toward 0 (truncation acts like noise, so the echo no longer refocuses),
but bigger true values still give bigger estimates. Since the score is corr² (scale-free), a squashed but
correctly ORDERED estimate still earns points. Running the full S3 with mps64 and pauli-path 1e-4 to measure this properly.
