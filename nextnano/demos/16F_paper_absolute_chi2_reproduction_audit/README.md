# Demo 16F — paper absolute-χ⁽²⁾ reproduction audit

Demo 16E reproduced this paper's **shape** and missed its **scale**:

| what | paper | Demo 16E | |
|---|---|---|---|
| ground transition E1−HH1 | 1.49 eV | 1.4927 eV | 0.2 % |
| excited transition E2−HH2 | 1.62 eV | 1.6456 eV | 1.6 % |
| simulated peak wavelength | ~1520 nm | 1517 nm (`case_02`) | 3 nm |
| graded/abrupt ratio | 0.513 | 0.519 (1.00 nm grade) | 1.2 % |
| **χ⁽²⁾(1550), ideal abrupt** | **2340 pm/V** | **31.0 pm/V** | **75×** |

A ~75–85× offset that is **the same on all ten of 16E's structures** is a
prefactor problem, not a physics problem. Demo 16F takes the prefactor apart.

**No optimization. No search. No free scale factor.** A convention may change
here only when a cited equation, crystallographic fact or published sentence
requires it, and every variant carries that citation in `justification()`.
`conventions16f.HELD_FIXED` lists the parameters the audit had the opportunity
to tune and declined to.

## One structure, not ten

The paper's ideal-abrupt **7.1 / 1.8 / 2.9 nm** coupled pair inside the full
**30 nm** period (18.2 nm AlGaAs period barrier). That is the structure whose
χ⁽²⁾ the paper states outright, so a reproduction either lands on a published
number or it does not.

## Targets

Three numbers the paper states **in words**, at 1550 nm:

| target | value | interfaces | source |
|---|---:|---|---|
| `ideal_abrupt` | **2340 pm/V** | abrupt | §3.1 |
| `eds_al_profile` | 1200 pm/V | measured Al profile | §3.1 |
| `eds_ga_profile` | 1363 pm/V | measured Ga profile | §3.1 |

Fig. 2d's ~4000 pm/V peak is **deliberately not a target**: it is read off a
figure, the repo's digitisation carries ±15 %, and it is inconsistent with the
2340 pm/V the same paper quotes for the *abrupt* case — which should be the
larger of the two. Reproducing three stated numbers with one implementation is a
much stronger claim than matching one curve by eye.

## The variant ladder

Cumulative, one decision per rung, so the table reads as a budget.

| variant | changed | why it is allowed to change |
|---|---|---|
| `legacy` | nothing | Demo 14/16E production; the number already on record |
| `paper_Nz` | N_z: period → well density (**×2**) | Methods §5.1: "N_z is the number of quantum wells per unit length"; Fig. 1a puts **two** GaAs wells in each 30 nm period |
| `paper_Nz_and_zone` | BZ edge: π/a → **2π/a** (k_max ×2) | GaAs is zincblende (FCC): X = (1,0,0) in units of 2π/a, so Γ→X is 2π/a. π/a is the *simple cubic* edge and does not describe this lattice |
| `independent_cartesian` | k integral: radial → Cartesian | **a control, not a correction** — must reproduce the row above exactly |
| `square_domain` | k domain: disc → square (×4/π) | reported as a sensitivity, **not promoted**: the paper's saturation argument is isotropic and therefore describes a radius |
| `open_hh_mj_factor` | hh m_j = ±3/2 applied (×2) | an **open** factor the paper does not state; reported so its size is visible, never promoted |

`promotable()` returns true only when every choice has a source that requires
it — so `square_domain` and `open_hh_mj_factor` can never become production.

## What the solver-free audit already settled

`--audit` needs no solver and no licence. Two results are already in:

**1. The k-space normalisation is correct — this is *not* where the 75× is.**
Two independently written implementations (`radial_integral` reduces the
integral analytically using isotropy; `cartesian_integral` quadratures the
genuine (kx, ky) plane and never assumes isotropy) agree to **≤1.4 × 10⁻⁵** on
three different integrands, on both the disc and the square, and the disc
constant case reproduces the closed form `g_s k²/(4π)` to **machine precision**.
The square/disc ratio comes out at **1.273 = 4/π**, the exact area ratio. No
stray 2π, no missing radial measure, no double-counted spin, no missing area
normalisation. The dimensional ledger closes on **m¹ C¹ J⁻¹ = m/V** with every
factor carrying a declared unit and nothing labelled "dimensionless sum".

> This audit caught a bug in its own closed-form check first — `analytic_square_constant`
> was written `g_s k²/π` instead of `g_s k²/π²`. That is what the check is for.

**2. Eq. 1 and Eq. 2 as printed differ by exactly 3, and no permutation count
closes it.** Eq. 1 carries `1/(2ε₀ħ²)` with an explicit `Σ_P`; Eq. 2 carries
`1/(6ε₀ħ²)` with none. Fed identical matrix elements:

| permutation set | terms | Eq1/Eq2 | |
|---|---:|---:|---|
| `identity_only` | 1 | **3.000000** | |
| `intrinsic_shg_input_swap` | 2 | 6.000000 | mixes tensor components |
| `full_index_permutations` | 6 | 18.000000 | mixes tensor components |

No integer multiplicity gives 1 — you would need ⅓ of a term. So Eq. 2's `1/6`
absorbs something Eq. 1's `1/2` and its permutation sum do not express as
printed. **This is an open discrepancy in the published pair of equations, and it
runs in the direction of the production number being too small by 3** if Eq. 1 is
taken as the authority. It is recorded and **never applied**.

Note the two swap-based sets are flagged: the paper states χ_xzx ≠ χ_xxz for
these wells, so exchanging the two input photon indices in (x, z, x) produces
(x, x, z) — a component the paper says is a *different number*. Arithmetic
agreement would not make such a set correct.

## The two gates 16E ran in warning mode

**Bound states — now strict, and it fails closed.** Every one of 16E's ten cases
recorded `physical_qc_valid = False` with one state entering the χ⁽²⁾ sum failing
the bound criterion, under `quasi_bound_policy: warn`. The paper says it uses
"the first two bound states in the heavy hole and conduction bands" and that two
bound states were guaranteed. **16E and the paper were therefore not applying the
same state selection**, however close the energies looked.

`bound_state_gate()` reports **E1, E2, HH1 and HH2 individually** — verdict,
energy, boundary probability, whether the state is inside Eq. 2's window, and the
criterion text — because "domain too short", "outer barrier too thin" and
"genuinely quasi-bound" are different defects with different fixes and a count
cannot tell them apart. It also records that heavy holes get the **weaker** test:
Demo 11 has no valence barrier-edge profile, so only the probability half runs,
and a hole that "passes" has passed less than an electron that passes.

> **Fixed defect.** The first version of this gate filtered on `in_chi2_sum`, a
> key `demo11._quasi_bound_records` does not use — it writes
> `within_chi2_state_window`. The filter matched nothing, so the failing list was
> empty, so the gate returned **`passed = True`** while printing
> `states in the chi2 sum: []`. That is why `--from-run` showed an empty list.
> The gate now certifies **only** when all four required states are present *and*
> all four pass; a missing state, an untested state or an unrecognised schema
> returns `passed = None` (**NOT CERTIFIED**), and no caller treats `None` as
> success. Four tests pin this, including one that replays the exact old schema.

**On `fail_case` vs `warn`.** The requested policy is `fail_case`, and the
verdict 16F enforces *is* `fail_case`. The mechanism differs for one concrete
reason: Demo 11 raises on `fail_case` at the point the diagnosis is written,
**before `envelopes.csv` exists**, which would deny the audit the wavefunctions it
needs to explain the failure. So the analysis runs under `warn` and 16F applies
the strict verdict to the per-state table — identical verdict, all artifacts
preserved. `--strict-abort` restores the hard abort; `adapter14` now reads the
policy from the config instead of hardcoding `"warn"`, defaulting to `"warn"` so
Demos 13, 14 and 16B–16E are unchanged.

**Outer domain — dipoles, not just energies.** Absolute χ⁽²⁾ rides directly on
`<ψ|z|ψ>`, which converges more slowly with domain size than eigenvalues do.
`domain_convergence()` therefore holds the position matrix elements to a 1 %
relative budget alongside the 1 meV energy budget, and reports them separately.
Energies converging while dipoles have not is *exactly* the pattern that
produces a correct resonance position with a wrong amplitude — so that
combination is called out explicitly rather than averaged into one verdict.

## Independent by construction

`variants16f.chi2_at` is a **second implementation** of Eq. 2, built on
`kspace16f` and `eq16f` rather than on the shared `chi2` module. When the
`legacy` rung reproduces 16E's recorded 31.0 pm/V for `case_02`, two
independently written evaluators agree and production `chi2.py` is corroborated.
If it does not, one of them is wrong and the audit has found it. Reusing
`chi2.py` here would have made that check impossible.

`demo16f.matrix_elements` likewise recomputes the overlaps and position matrices
from the envelopes, and `cross_check_recorded` compares all eight against the
values the producing run stored.

## Regression anchors

The ladder was validated on Demo 16E's licensed `case_02` envelopes. These values
are pinned in `conventions16f.LADDER_REGRESSION_PM_PER_V` and checked on every
run:

| rung | χ⁽²⁾(1550) pm/V | |
|---|---:|---|
| `legacy` | **30.99** | reproduces 16E's recorded 30.994 — **two independently written evaluators, one number** |
| `paper_Nz` | 61.99 | exactly ×2, as N_z enters linearly |
| `paper_Nz_and_zone` | 84.04 | ×1.356 from the zincblende zone edge |
| `independent_cartesian` | 84.14 | the control: 0.12 % from the row above |

A drift is not automatically an error — newly solved wavefunctions may genuinely
differ — but it is never allowed to pass silently, because the *other* thing that
moves these numbers is somebody editing a convention.

## The licensed experiment

`--solve` performs all remaining licensed work itself. It uses the authoritative
machine configuration and Demo 16E's solver infrastructure unchanged: 16E's
renderer, parser gate, realized-composition gate, required-quantum-output gate,
solve, and Demo 11's optical analysis through Demo 14's adapter. 16F adds only
the domain sweep, the strict bound verdict and the ladder.

One structure, three domains:

| | |
|---|---|
| structure | 7.1 nm GaAs / 1.8 nm Al₀.₅₅Ga₀.₄₅As / 2.9 nm GaAs, s = 0.42, **abrupt** |
| outer AlGaAs | **18.2 nm** (the paper's own period barrier), 25.0 nm, 35.0 nm |
| per solve | E1, E2, HH1, HH2; E2−E1, HH1−HH2; E1−HH1, E2−HH2; all four ⟨ψ_e\|ψ_hh⟩; all six ⟨ψ\|z\|ψ⟩ and both diagonal differences; boundary probability and bound criterion per state; χ⁽²⁾(1550) |
| convergence | eigenenergies (1 meV) and position matrix elements (1 % relative) reported **separately** |
| then | the ladder on the newly solved wavefunctions, `well_density` + `gamma_to_x_2pi_over_a`, radial **and** independent Cartesian |

The final report states whether the domains are converged, which state (if any)
is not bound, the best physically justified absolute χ⁽²⁾, and the remaining
factor versus 2340 pm/V.

## Commands

Runs anywhere, no licence:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --audit
```

The licensed experiment — three solves, gates, ladder, final report:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --solve
```

See what it will do before it does it:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --plan
```

The ladder alone, from an existing Demo 16E run, with no new solve:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --from-run <16E_run_dir> --case case_02
```

Convergence across runs this demo did not produce:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --converge 18.2=<run1> 25=<run2> 35=<run3>
```

## Expected outcome, stated in advance

Measured, not predicted: N_z (×2) and the zincblende zone edge (×1.356 at
1550 nm) took `case_02` from **30.99 → 84.04 pm/V**. Against 2340 pm/V that
leaves **27.8×**.

**That is the honest result and it was not supposed to close.** What it does is
remove two known ambiguities, narrowing the remaining discrepancy from "maybe any
of our quantum-well physics is wrong" to a specific short list:

* the factor of **3** between Eq. 1 and Eq. 2 as printed (measured, above) —
  reported, never applied;
* the heavy-hole m_j multiplicity the paper does not state (**×2** if it
  applies) — the open ladder rung, never promoted;
* whatever the strict bound-state gate turns up on the newly solved states;
* whether the position matrix elements are converged at the paper's own 18.2 nm
  period barrier — energies converging while `<z>` has not is exactly the pattern
  that gives a right resonance position with a wrong amplitude.

Even granting both unresolved factors (3 × 2 = 6) the gap would still be ~4.6×,
so neither is a hidden answer. They are bounded, cited and reported separately.

16E's `case_09`/`case_10` equivalence — 0.0 composition difference, 0.0 meV
energy difference, 1.7 × 10⁻¹³ relative χ⁽²⁾ — already proves the grading
renderer is **not** the source of the amplitude problem.

## What must not happen

* No `absolute_scale_factor`. Fitting one answers the question by assuming it.
* `r_e_hh_nm = 0.751` stays. It has an independent basis (Ramesh 2023 APL,
  VASP/HSE06) and is corroborated by the GaAs Kane-model value
  `r_cv = ħp_cv/(m₀E_g) = 0.738 nm`. Changing it to raise χ⁽²⁾ is parameter
  fitting.
* Γ = 5 meV, two states per band and the 0.10 BZ fraction stay: the paper states
  all three explicitly in Methods §5.1. Only *which boundary* the fraction is
  taken of is under investigation.
* A variant is never promoted because its number is larger. `promotable()`
  enforces this in code.
