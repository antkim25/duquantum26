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

## Near-Clifford vs generic (explains when Pauli-path works)
Fraction of u3 gates at exact quarter-turn (Clifford) angles: S1 15%, S2 16%, **S3 90%**.
Clifford gates map one Pauli term to one term (no branching), so Pauli-path stays exact on S3 and explodes/collapses on S2.

S3 Pauli-path 1e-4, 19 qubits: FAST jobs (5-25 s) are exact to 2 decimals (q9,10,11,12,13,15,16,17);
SLOW jobs (80-130 s) are often wrong (q2, q8 -> 0; q7 -0.30 vs -0.51). Slow = lots of branching = truncation damage.
=> runtime is a per-qubit reliability signal.

## Probe of G circuits with Pauli-path 1e-3 (qubits 0,4,8,12): ALL exactly 0.000, ~5 s each, for G2, G3 and G4.
Control: S3 at 1e-3: q12 -> 0.000 (exact -0.65), q17 -> -0.33 (exact -0.81).
=> 1e-3 is too coarse even for near-Clifford circuits, so the probe is INCONCLUSIVE for G3/G4. Re-probe at 1e-4.
G2 is very likely generic anyway (smooth MPS light-cone pattern; MPS says q0 = +0.999 where PP says 0).

## Hidden SDK options (found by reading the SDK source, not on the main page)
- device "pauli-path.gpu" (added Oct 2025)
- option "pauli_path_weight_cutoff" (pauli-path.gpu only): truncate Pauli strings by weight
- "pauli_path_circuit_transpilation_level" 0-3 (default 2; 3 = aggressive gate-count reduction)
- force_run=True (mps only): bypass server-side runtime limits
- MPS default bond dimension is 256 (we used 64); max 2048 on mps.cpu, 4000 on mps.gpu
- Pauli-path jobs hold $25 each while running (charged $0 so far): only one at a time on a $30 balance

## Layouts confirmed from gate counts (two-qubit gates per layer inside one U)
S2 7.5, G1 14.5, G2 17.5 = 1D chains (n-1 links, alternating layers); S3 12.2 = 5x6 grid (49 links / 4);
G3 15.0 = 6x6 grid (60 links / 4); G4 15.8 = 2D with 63 links.
S3 pauli-path 1e-4 on 19 qubits: corr² = 0.93 (the first 5 were lucky; slow jobs collapse).
Plan (with teammate): G3/G4 -> pauli-path 1e-4 (if near-Clifford like S3); G2 -> MPS chi 128/256 on slope qubits 4-11, 27-31.

## G2-G4 runs, Oct 24 (Colin's account, token fingerprint 1b9fda99f0, $29.93 start balance)
Free plan limits (`bq plan`): mps/pps job time 15 min, 1000 mps/pps jobs/day, no gpu pauli-path.
`run_circuit.py` now saves per-job `metrics` (run_time_ms, queue_time_ms, cost, status) in each results JSON.
Logs for every run are in `logs/`.

### Test round (`test_round.sh`, one qubit per setting)
| circuit | command | value | job run time | actual cost |
|---|---|---|---|---|
| G3 q14 | `run_circuit.py G3 --device pauli-path --threshold 1e-4 --qubits 14 --batch 1` | 0.000000 | 205 s | $0.00 |
| G4 q14 | `run_circuit.py G4 --device pauli-path --threshold 1e-4 --qubits 14 --batch 1` | 0.000000 | 144 s | $0.00 |
| G3 q14 | same + `--level 3` | 0.000000 | 120 s | $0.00 |
| G2 q8 | `run_circuit.py G2 --device mps.cpu --chi 128 --qubits 8` | +0.106 (chi64 +0.306) | 130 s | $0.00 |
| G2 q8 | `--chi 256` | -0.008 | 135 s | $0.00 |
| G2 q8 | `--chi 512` | refused: NOT_ENOUGH_FUNDS, needs >= $82.26 balance (force_run would risk the whole balance) | - | $0.00 |

=> Pauli-path 1e-4 gives exactly 0 on G3 and G4 (and on G3 at level 3, which is ~40% faster). Exactly 0 = every
kept term is off-diagonal, i.e. the truncation collapse seen on S2. Like the 1e-3 probe, G3/G4 look generic,
not near-Clifford like S3. Running all qubits at 1e-4 would just produce zeros, so it was not run.
=> MPS run time barely depends on chi (chi128 ~2 min, chi256 ~2.3 min), but the funds hold grows:
chi256 holds ~$21.76 per job (one at a time on $30), chi512 needs $82.

### G2 MPS chi 128, all 36 qubits
`python run_circuit.py G2 --device mps.cpu --chi 128 --qubits 4,...,31 --batch 5` then the rest with `--batch 4`.
Jobs 64-145 s (median 115 s), 5 in parallel, ~19 min total for 36, actual cost $0.00.
Output: `submissions/G2_mps.cpu_chi128.csv`.
Compared with chi64: every slope qubit drops by 0.09-0.20 (e.g. q6 0.60 -> 0.40, q8 0.31 -> 0.11), but the ordering
holds: corr²(chi64, chi128) = 0.975 on the 13 slope qubits, 0.967 on all 36. Not converged yet
(q8 keeps falling: 0.31 / 0.11 / -0.01 at chi 64 / 128 / 256). Do not mix chi levels in one CSV: the shift is a
level offset, so chi128 slope + chi64 plateau would distort the correlation.

### G2 MPS chi 256, all 36 qubits (done)
`python run_circuit.py G2 --device mps.cpu --chi 256 --qubits <slope first, then rest> --batch 1`
(`--batch 1` because each chi256 job holds ~$21.76.) Jobs 59-173 s (median 139 s), one at a time,
~80 min wall time for 36 (19:21-20:40 UTC), actual cost $0.00. Output: `submissions/G2_mps.cpu_chi256.csv`.

| q | chi64 | chi128 | chi256 |
|---|---|---|---|
| 2 | +0.953 | +0.916 | +0.854 |
| 4 | +0.834 | +0.731 | +0.601 |
| 6 | +0.595 | +0.401 | +0.227 |
| 8 | +0.306 | +0.106 | -0.008 |
| 10 | +0.268 | +0.103 | +0.035 |
| 12-26 | ~0 (±0.06) | ~0 (±0.03) | ~0 (±0.01) |
| 28 | -0.030 | -0.124 | -0.181 |
| 30 | +0.433 | +0.310 | +0.190 |
| 32 | +0.886 | +0.850 | +0.804 |
| 0,1,34,35 | ~+0.998 | ~+0.995 | ~+0.99 |

corr² between runs (all 36): chi64-chi128 0.967, chi128-chi256 0.981, chi64-chi256 0.904. Slope qubits only:
chi128-chi256 0.987, chi64-chi256 0.938.
=> Each doubling of chi narrows the light cone: slope values drop by 0.1-0.2 per step, the plateau gets cleaner (noise
±0.06 -> ±0.01), q28/q29 go more negative. The shift is shrinking (64->128 differs more than 128->256), so chi256
is the closest to converged we can reach (chi512 needs an $82 balance). Submit chi256 for G2 (chi64 scored 426/600).

### G3 MPS chi 128: stopped after 4 qubits (too slow, and billed)
`python run_circuit.py G3 --device mps.cpu --chi 128 --batch 4 --wait-funds` (new `--wait-funds`: retry when
another run holds the balance).
| qubit | value | job run time | actual cost |
|---|---|---|---|
| 0 | -0.035 | 894 s | $0.00 |
| 1 | -0.055 | 1141 s | $0.48 |
| 2 | +0.000 | 1184 s | $0.50 |
| 3 | -0.002 | 1186 s | $0.50 |
Total $1.48 actually charged. The `--budget 1` cap stopped new submits; the 3 jobs in flight (q4-6) were canceled at $0.
=> On the 6x6 grid MPS jobs take 15-20 min (10x G2's chain) and past ~15 min they are billed (~$0.50/job).
Full G3 would be ~$18 and ~3 h, and the values come out ~0 like MPS on S3. MPS is not the method for G3.
Next for G3: pauli-path 1e-4 probe on corner/edge qubits (0, 5, 30, 35, 2, 33), where true values are likely far
from 0. q14 = 0 is not proof of collapse: middle qubits are probably scrambled to ~0 anyway.
## From the official docs (OTOC tutorial, devices/pricing page, "Choosing a quantum simulator")
Pricing: cpu FREE (60 min/job); mps.cpu and pauli-path (cpu) FREE up to 15 min/job, then $1/h (min $0.20);
mps.gpu and pauli-path.gpu $3/h. Hybrid notebook SMALL = $0.20/h (24 h ~ $4.80 of credits), LARGE $1.50/h.
Pauli-path speed (127-qubit benchmark): delta 1e-4 -> cpu 324 s vs gpu 1.2 s; 5e-5 -> 1295 s vs 1.6 s. GPU wins below ~1e-3.
MPS speed: cpu time ~ chi^2.1, gpu ~ chi^1.5; crossover chi ~128; chi >= 256 -> mps.gpu (2x at 256, ~7x at 1024).
  => G2 chi 64 took 56 s, so chi 128 ~ 2.5 min, chi 256 ~ 11 min on mps.cpu (inside the free 15 min).
Convergence: sweep the knob until the answer stops moving; MPS/PP can get WORSE before better (non-monotonic).
OTOC tutorial: these circuits are OTOC(2) = <(B(t)M)^4> (sign problem; truncation kills terms that would refocus).
  Pauli paths return 0 on random circuits at every threshold but converge on near-Clifford circuits.
  Deep in the scrambled region, generic circuits give ~0 +- 2^(-n/2) (~0.004 at 36 qubits): no signal there.
  The circuit-specific signal is in the band just behind the light-cone front -> for G2 that's the slope qubits.

## Pauli-path verdict for G3/G4: generic circuits, Pauli-path fails (14:5x)
- pauli-path.gpu works: S3 q12 at 1e-4 = -0.654448 (exact -0.654), 5 s. But each GPU job is billed at least $0.20.
- G3 q14: 1e-4 -> 0.000; 1e-5 -> REJECTED ("threshold too small... memory overflow") = Pauli terms explode = not near-Clifford.
- G4 q14: 1e-4 -> 0.000; 1e-5 -> 0.00006 (47 s). Collapse, as on S2.
- Earlier: G3 q0 cpu 1e-4 -> -0.015 after 171 s.
- Two CPU pauli-path jobs running at once hold $50 and block everything else (error showed "pending jobs estimated cost: $50.00").
=> Switch G3/G4 to MPS. First get any submission (G3/G4 were at 0), then raise chi on the light-cone-front qubits.

## Pauli-path re-check with a proper control (~15:30)
Worry: maybe G3 (6x6 grid, like S3) is near-Clifford by design, and our single probe qubit (14) was misleading
(on S3, q14 also gave 0 at 1e-4 even though S3 is near-Clifford).
- Control: S3 q12 at 1e-5 on pauli-path.gpu -> -0.653 in 6 s (works; 1e-5 is fine on a near-Clifford circuit).
- G3 at 1e-4 on q0, q5, q35 (+ q14 earlier): all exactly 0.000. G3 at 1e-5: rejected (memory overflow).
- G4 at 1e-4 on q0, q5, q35 (+ q14 earlier): all exactly 0.000.
=> G3 and G4 are generic (not near-Clifford). On S3 the same pipeline is near-exact; on G3/G4 every term is truncated.
   Samples teach the two cases: S3 = near-Clifford grid (Pauli-path), S2 = generic chain (MPS).
   G3/G4 = generic GRIDS: the hardest case (Pauli-path collapses, MPS is slow). Stay with MPS.
GPU spend so far: 12 jobs x $0.20 = ~$2.40.

## G3/G4 MPS progress and timing (~16:00)
- G4 chi 64: 1-6 min/job (free), values -0.09..+0.87 with clear structure (light-cone front visible).
- G3 chi 64: 9-17 min/job; jobs over 15 min billed for the WHOLE runtime at $1/h (~$0.42 each). Budget cap stopped it at $2.10.
- G3 chi 48: ~14 min/job (barely free), values ~1e-6: MPS has lost the signal on G3 entirely.
  Time barely dropped from chi 64 -> 48, so bond dimension isn't what dominates G3's runtime.
- shots=1 test (G2 q4 chi 64): same value (+0.834023) as 1024 shots, not faster. Sampling isn't the cost;
  the expectation value is exact regardless of shots.
- G3 = generic 6x6 grid, fully scrambled: hardest case for both MPS and Pauli-path. Expect a low score there.

## G4 chi 64 scored 0/1000 (~17:19): MPS at chi 64 is garbage on 2D circuits
- Full S3 check (30 qubits, exact known): mps chi 64 gives q17 exact -0.81 -> +1.00, q29 +0.17 -> -0.95,
  q27 +0.96 -> +0.08. Wrong values of LARGE magnitude, not just squashed toward 0. So G4's "structure" was artifacts.
- Why: MPS is a 1D chain over qubit index; a 2D grid cuts many couplers across each bond, so the needed chi explodes.
- Per U: S3 392 cz / depth 32; G4 756 cz / depth 48 (deeper than S3).
- SDK knobs checked (bluequbit 0.19.0b1 source): cloud accepts only mps_bond_dimension,
  pauli_path_truncation_threshold (min 1e-5), pauli_path_circuit_transpilation_level, pauli_path_weight_cutoff.
  mps_truncation_threshold (default 1e-10) exists only in local mode. No qubit-reordering option for MPS.
- Jobs report run_results: mps_build_time (MPS) and max_paulis (Pauli-path), a measure of how many terms survived.
- Pauli-path 1e-4 is NOT conclusive per qubit: on S3 it returned 0 for q2 (+0.21), q8 (+0.26), q14 (+0.03).
  G4 at 1e-5 has only been tried on q14. Next: G4 pauli-path.gpu 1e-5 on more qubits, and calibrate high-chi MPS on S3.

## G2 chi 256 (Colin, all 36 qubits, free, ~1.5-3 min/job): 547/600 (corr^2 0.91)
- Not converged yet: 128 -> 256 still moves the front qubits by -0.06..-0.17 (q4-11, q27-33), always downward;
  everything else moves < 0.025. Shift per doubling barely shrinks (64->128 ~ -0.19, 128->256 ~ -0.17 on q6/q7).
- chi 512 on mps.cpu should take ~10 min/job (chi^2.1), still inside the free 15 min, but the submit needs
  force_run (server wants an $82 balance). Run it with --force-run --max-minutes 14 so nothing gets billed.
- The git merge of Colin's branch corrupted results/G2/mps.cpu_chi128.json and results/G3/pauli-path_th0.0001.json
  (two versions spliced together). Rebuilt both from the two merge parents; no values lost.
  Lesson: two machines must never write the same tag; give each account its own --tag.

## S3 calibration of MPS at chi 512 on mps.gpu (~5 min, ~$0.31/job; needs --force-run)
| S3 qubit | exact | chi 64 | chi 512 gpu |
|---|---|---|---|
| 17 | -0.812 | +1.000 | -0.873 |
| 29 | +0.166 | -0.950 | +0.907 |
| 27 | +0.958 | +0.084 | +0.096 |
=> MPS is still unreliable on a 2D grid at chi 512 (wrong sign / magnitude on 2 of 3).

## BlueQubit benchmarking paper (arXiv 2607.09882, shared by organizers)
- PPS error is NON-MONOTONIC in delta: on 127q kicked Ising the error PEAKS near delta ~5e-5 and only recovers below 1e-5.
  The API's 1e-5 floor is "a software-imposed limit rather than a hardware one"; their PPS-GPU reached 2.9e-6.
  => Our G3/G4 Pauli-path zeros at 1e-4..1e-5 may be the error peak, not proof the circuits are generic.
- MPS on a 46q peaked circuit needed chi ~1536 on GPU (~22 h/run) for a correct answer; at intermediate chi,
  truncation flips signs of local <Z_i> (same as our S3 sign flips).
- MPS backends are quimb; CPU runs on 2 cores ("small1"). GPU wins only for chi >= ~256.
| 12 | -0.655 | -0.004 | -0.113 |
(S3 q9 cancelled: 3 of 4 wrong is enough. MPS ruled out for 2D grids.)

## Pauli-path on GPU, fine thresholds (~18:30) -- the paper's non-monotonic convergence, seen directly
S2 (generic 16q chain, exact known), pauli-path.gpu:
| S2 qubit | exact | 1e-4 | 2e-5 |
|---|---|---|---|
| 10 | +0.58 | +0.005 | +0.495 |
| 12 | +1.00 | +0.321 | +0.930 |
| 0  | ~0    | -0.036 | -0.045 |
| 4  | ~0    | +0.005 | -0.043 |
=> 2e-5 is accurate on a generic circuit; 1e-4 kills all but the strongest signal (not a uniform rescaling).
1e-5 on S2: FAILED_VALIDATION (memory). Weight cutoff 6/10 and transpilation level 0/3 do NOT get past the check:
the server sets a per-circuit minimum threshold. Each GPU job ~5-20 s, $0.20.
G4 at 2e-5: q4 0.000, q22 0.000, q36 -0.012. At 1e-5: q0 8e-5, q4 6e-4, q14 6e-5, q11 rejected.
=> G4 needs a threshold below what the server accepts. Colin's 2e-5..5e-5 rejections were on CPU pauli-path.
