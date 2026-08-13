# Demo 17b — prefactor, degeneracy and unit-cell matrix scale audit

Pure Python. **No nextnano++, no licence, no solver.** Runs in about a second.

Demo 17 closed the envelope side: matrix elements moved ≤2.4 % and transition
energies ≤0.22 % when the Dirichlet box went from 2 nm to 30 nm padding, origin
independence held at 2.7e-13, and two independently written Eq. 2 evaluators
agreed to 0.8 % (84.70 vs 16F's 84.04 pm/V on `case_02`). The residual **27.6×**
against the paper's 2340 pm/V is therefore in the **prefactor**, and Demo 17b
takes it apart.

## Why this can be exact arithmetic

Every quantity swept here — N_z, the permutation/degeneracy count, the spin
weight, r_e,hh — multiplies the **whole** Eq. 2 triple sum. None enters a
denominator, a matrix element, or the k dependence, so none can change the
lineshape or the relative weight of any term. Each sweep is an exact
multiplier, and it stays exact even when the sum is only available as a recorded
number.

That is asserted rather than assumed: `verify_multiplicative` re-evaluates the
sum with and without each factor whenever states are available, and refuses to
report a multiplier that does not come out at the analytic value. A negative
control confirms the check can fail.

## Results

Run on `case_02` (abrupt, the paper's 2340 pm/V structure) and `case_01`
(graded twin), from Demo 17's committed hand-off.

| | sweep | variant | × | status |
|---|---|---|---:|---|
| **A** | N_z counting length | period, 2 wells / 30 nm | **1.000** | promoted (baseline) |
| | | active layer, 2 wells / 10 nm | 3.000 | reported only |
| | | period, 1 pair / 30 nm | 0.500 | legacy, superseded |
| **B** | permutation | SHG degeneracy | 2.000 | reported only |
| | | Eq. 1 / Eq. 2 | 3.000 | reported only |
| **C** | HH spin / Kramers | **already counted once** | **1.000** | **closed** |
| **D** | Kane dipole | E_p = 28.8 eV, E_g = 1.424 eV | **0.959** | **closed** |

| reading | product | χ⁽²⁾ (case_02) | remaining vs 2340 |
|---|---:|---:|---:|
| baseline (Demo 17) | 1.000 | 84.70 pm/V | 27.63× |
| defensible | 1.000 | 84.70 pm/V | 27.63× |
| maximal (upper bound) | 8.635 | 731.39 pm/V | 3.20× |

**The defensible product is 1.0.** Nothing in the published text requires any of
these factors, and the audit does not promote one because it makes the number
larger.

### Sweep D closes r_e,hh — in the opposite direction to the usual guess

$$r_{e,hh}=\frac{\hbar}{E_g}\sqrt{\frac{E_p}{2m_0}} = 0.7356\ \text{nm}$$

for GaAs (E_p = 28.8 eV, E_g = 1.424 eV at 300 K, the temperature Demo 17 solved
at). That is **2.0 % from the published VASP/HSE06 value of 0.751 nm**, so the
multiplier is (0.736/0.751)² = **0.959 — slightly below one**.

An r of 1.28 nm would require **E_p = 87.2 eV** (GaAs: 28.8) or **E_g = 0.818 eV**
(GaAs: 1.424). Neither is GaAs. The Kane relation therefore *confirms* the
legacy constant and removes r_e,hh from the list of suspects; it does not supply
a 2.9× boost. The audit prints both the value and the inputs that would have
been needed, so the discrepancy is attributable rather than mysterious.

### Sweep C closes the m_j ×2 open factor

Not a configurable multiplier — the audit reads the answer out of the code.
`inspect.getsource` finds `spin_degeneracy` applied **once**, in
`chi2._k_grid`'s weight vector, and **zero** times in `chi2_spectrum`'s state
sum. The one-band HH solver returns orbital envelopes and does not resolve
m_j = ±3/2, so a spin weight of 2 *is* the Kramers doublet.

Verdict: **already counted, once, correctly. Multiplier 1.0** — an additional
m_j factor of 2 would double-count. Demo 16F listed this as an open factor
bounding part of the gap; it can now be struck off rather than bounded.
Corroborated by Demo 18 rows G/H, which measured the g_s = 1 vs 2 ratio at
exactly 2.0 independently.

### Sweeps A and B stay open, and B must not be multiplied out

- **A** — the period reading (2 wells / 30 nm) describes the grown stack. The
  active-layer reading (2 wells / 10 nm, ×3) describes a medium that is entirely
  quantum well with no barriers; comparing that to anything grown requires
  putting the 10/30 fill factor back, which returns exactly the period reading.
  Promoting it would make the paper's number describe a material nobody grew.
- **B** — the Bloembergen/Boyd SHG degeneracy factor of 2 is *precisely what a
  permutation sum over the two input photons produces*, and 16F measured
  Eq. 1 / Eq. 2 = 3.000000 using `identity_only`, i.e. with no permutation sum
  applied. Multiplying both very likely counts the same bookkeeping twice. They
  are reported separately, marked `mutually_exclusive_with` each other, and the
  maximal product carries an explicit warning.

## Verification

| check | result |
|---|---|
| Independent Eq. 2 (angular-frequency, ħ² in prefactor) vs `_shared/chi2.py` (energy form) | **4.9e-15** relative |
| Prefactor recomputed from CODATA vs Demo 18's `production_prefactor` | 113.39633764994086, rel **0.0** |
| `verify_multiplicative` on N_z ×3, extra ×2, spin 2→1, r ×1.5 | 4/4 verified |
| Negative control (wrong expectation) | correctly rejected |
| Both higher loading tiers | 9/9 multipliers verified |

The angular-frequency form is deliberate: `chi2.py` writes the denominators in
energy, which cancels the ħ² that the published Eq. 3 carries explicitly. That
is a legitimate rewriting and exactly the kind of step that can hide a factor, so
this module does it the other way. Agreement is evidence about both.

## Loading tiers

| tier | needs | sum rebuilt? |
|---|---|---|
| `envelopes` | `envelopes.csv` | yes, from signed amplitudes |
| `matrix_elements` | `matrix_elements.json` | yes, from stored matrices |
| `summary` | `physics_summary.json` only | **no** — recorded value used |

The repo's current hand-off is `summary` tier, because `physics_summary.json`
records the *diagonal* overlaps but not ⟨ψ_e1|ψ_hh2⟩ or ⟨ψ_e2|ψ_hh1⟩. Every
multiplier is still exact; only the numerical re-verification column shows `-`.

To reach a higher tier, copy from the work laptop:

```powershell
$run = "C:\nn_results\17_paper_chi2_reproduction_corrected\demo17_<stamp>"
Copy-Item "$run\cases\case_02\physics\optical\parsed\*.json" "demo_results\demo_17\paper_target_case_02\"
Copy-Item "$run\cases\case_02\physics\optical\parsed\envelopes.csv" "demo_results\demo_17\paper_target_case_02\"
```

Artifacts are looked up under `paper_target_<case>/`, `<case>/`,
`<case>_<filename>`, or the full run tree. A bare top-level filename is
deliberately **not** matched, so one case's matrices can never be silently
reported as another's.

## Files

| file | what it owns |
|---|---|
| `demo17b.yaml` | the sweep definitions, every rationale, and what is promotable |
| `prefactor_audit17b.py` | tiered loader, independent Eq. 2, sweeps A–D, the budget |
| `run_demo17b.py` | CLI and the summary tables |

## Commands

```bash
python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py
```

```bash
python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py --json demo_results/demo_17b/audit.json
```

```bash
python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py --case case_02 --quiet
```

## Where the gap now stands

| | factor | status |
|---|---:|---|
| Demo 16E | 75× | starting point |
| Demo 17 (N_z, zone edge, box) | **27.6×** | measured, corrections applied |
| 17b sweep C (m_j) | — | **closed**: already counted |
| 17b sweep D (r_e,hh) | — | **closed**: Kane confirms 0.751 nm |
| 17b sweep A or B, if either were promoted | 9.2× or 3.2× | **open**, not promotable |

Three demos, two independently written Eq. 2 implementations and two solver
domains all agree on ~84 pm/V. The quantum-well physics, the k-space
normalisation, the dimensional ledger, the unit-cell dipole and the spin weight
are now all excluded. What remains is a **counting convention in the published
equations** — and 17b's finding is that the two candidates for it are probably
one factor, not two.
