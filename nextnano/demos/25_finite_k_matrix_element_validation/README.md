# Demo 25 - Finite-k matrix elements and extended-state Professional validation

Demo 25 acquires the one thing Demo 24 proved was still missing: nextnano++ Professional state
output at **every** finite k, so that `O_nm(k)`, `z_e,nl(k)` and `z_hh,ml(k)` can be calculated
instead of frozen at their k=0 values.

It is **not** a repeat of Demo 23. The physical structure is inherited from Demo 23 unchanged -
`config25.py` loads `demo23_config.yaml` and copies the geometry, materials, mesh and solver
blocks verbatim, and a test fails if `demo25_config.yaml` ever restates one of them. Only three
things differ: the k block, the number of solved states, and which per-k outputs are requested.

## Why Demo 23 only ever produced `k00000`

Demo 23's deck asked for `all_k_points = yes` on `output_states`, `transition_energies`,
`dipole_moment_matrix_elements` and `momentum_matrix_elements`, and still got state and matrix
files at k=0 only. The reason is visible in the deck:

```
k_integration_disabled{}
dispersion{ path{ ... num_points = 301 } }
```

`all_k_points` follows the **k-integration grid**, not the dispersion path. With
`k_integration_disabled{}` that grid holds exactly one point, so there was exactly one file set
to write. The `dispersion{ path{} }` block is a separate mechanism that emits energies, masses
and k vectors only - which is precisely the data Demo 23 did get.

Demo 25 therefore enables `k_integration{}`. That is the leading hypothesis, not a certainty,
which is why the pilot tests it against the alternatives rather than assuming it.

## Two stages, and the gate between them

**The pilot is mandatory.** `--production` reads `outputs/PILOT_GATE.json` and refuses to start
unless it says PASS. There is no code path in which Demo 25 substitutes `M(k)=M(0)` and calls the
result a finite-k validation.

The pilot runs six tiny variants, each isolating one candidate explanation, so a single
work-laptop trip settles the syntax question:

| Variant | Question it answers |
|---|---|
| `A0_control_demo23_style` | Control: does the Demo 23 configuration still give only `k00000`? |
| `A1_kint_nodensity` | Does `k_integration{}` alone produce multi-k state output? |
| `A2_kint_density` | Does `no_density = yes` suppress the k-integration loop? |
| `A3_kint_subdirs` | Does per-k output need `k_point_subdirectories = yes`? |
| `A4_kint_symmetry_C4` | How does `symmetry` change the emitted k-point set? |
| `A5_kint_plus_dispersion` | Can `k_integration` and `dispersion{path{}}` coexist for cross-check? |

The gate is filesystem-based. A zero exit status is not accepted as evidence, because Demo 23
exited cleanly and still wrote only `k00000`. `pilot_audit.py` counts the files that actually
exist, per k point, and additionally requires an identifiable k-vector file - finite-k data that
cannot be associated with a k value is not usable.

## Running it

On the **work laptop** (nextnano++ Professional). The repo must have
`nextnano/config/paths.local.yaml` pointing at the Professional executable, database and license;
`--pilot` and `--production` refuse to run against a Free build.

```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --preflight
```
```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --pilot
```
```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --pilot-audit
```
```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --production
```
```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --analyse
```

Stop after `--pilot-audit` if the gate fails and read `outputs/PILOT_BLOCKER_REPORT.md`.

### Watching progress

Every stage writes to `demo_results/demo25/progress.json`, so progress can be read from a second
terminal while the solver runs:

```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --progress --watch
```

The whole-run bar is weight-based; the running stage's ETA comes from measured throughput. A
stage with nothing measured yet reports `unknown` rather than inventing a number.

## How long it takes

Calibrated against the Demo 23 production run on the work laptop, which solved 301 dispersion
k points for 14 states in **10 min 20 s**.

| Stage | Machine | Estimate | Notes |
|---|---|---|---|
| `--preflight` | any | seconds | deck generation plus `--parse`; works with a Free build |
| `--pilot` | Professional | **5-20 min** | 6 variants x 4 k points, but with 32 states and full envelope output per k |
| `--pilot-audit` | any | seconds | filesystem only |
| `--production` | Professional | **1-3 h** | 301 k points at roughly 10-30 s each |
| `--analyse` | any | 2-10 min | parsing dominates; envelope files are numerous |

Disk is the other cost. Demo 23 wrote 18 MB per case with envelopes at k=0 only, for 14 states.
Demo 25 requests 32 states at every k, so expect **order 10-15 GB** for a 301-point production run.

**These are estimates, and the code does not rely on them.** The pilot measures seconds-per-k and
bytes-per-k for real, and `pilot_audit.recommend_k_points` sizes the production grid against the
`max_projected_hours` and `max_projected_output_gb` budgets in `demo25_config.yaml`. If 301 points
would blow the budget, it recommends a smaller matrix-element grid and says which budget was
binding. That is sound physics as well as sound engineering: the energies set the resonance
positions and need fine sampling, while the matrix elements vary slowly with k, so a coarser M(k)
grid interpolated onto the fine energy grid loses very little. `interpolate_onto` refuses to
extrapolate beyond the computed k range.

## What Demo 25 will and will not conclude

The `~2.296 eV` search has a rule built into it: **an energy match is never enough.** Every
candidate is also scored on envelope overlap and oscillator strength, and any candidate involving
a state outside the barrier gap is flagged as a Dirichlet box state of the quantum region, whose
energy depends on the region width rather than on the physics. Demo 24 established that no
bound-bound transition in this structure can exceed the 2.145 eV barrier gap, so a bound
candidate at 2.296 eV would contradict that and needs the stronger evidence.

Demo 25 does **not** tune layer widths, Al fractions or grading to fit the paper curve. If
geometry becomes the leading remaining explanation, the recommendation is Demo 26.

## Physics conventions this demo commits to

An 8-band k.p state is a spinor, so inner products and position matrix elements are summed over
all eight components:

    <a|b>   = sum_c integral conj(a_c(z)) b_c(z) dz
    <a|z|b> = sum_c integral conj(a_c(z)) z b_c(z) dz

The paper's Equation 2 is written in one-band envelope language. The bridge is that the kp8
electron-like states are CB-dominated and the hole-like states HH-dominated, so the Equation 2
quantities are the full spinor products for the physically corresponding states. That is a
modelling choice, not an identity, so the CB and HH purity of every state is reported next to
every matrix element.

State identity follows **character**, not energy order. Demo 24 found that Demo 23's `hh2` was
97.6% light-hole precisely because an ordering rule cannot tell HH from LH.

`nextnano`'s own `overlap_integrals{}` block has no `KP8` option in this version, so kp8 overlaps
must be reconstructed from envelopes. Where nextnano does export momentum and dipole matrix
elements directly, they are kept as an independent cross-check rather than substituted.

## Tests

```bash
python nextnano/demos/25_finite_k_matrix_element_validation/run_demo25.py --tests
```

47 cases covering structure inheritance and drift detection, deck generation, the pilot gate
logic, production sizing, spinor normalization, overlap conjugate symmetry, z-matrix hermiticity,
`M(k)/M(0)` behaviour, the reduction of the finite-k engine to the frozen engine when `M` is
constant, character-based tracking through an energy-order swap, the optical-relevance rule,
progress-tracker persistence and gate blocking, and the fail-loud contracts: no solver launch
outside the runner, no fabricated finite-k data, no production without a passing gate, and Demo 23
and Demo 24 left untouched.
