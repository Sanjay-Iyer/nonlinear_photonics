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

**Bound states — now `fail_case`.** Every one of 16E's ten cases recorded
`physical_qc_valid = False` with one state entering the χ⁽²⁾ sum failing the
bound criterion, under `quasi_bound_policy: warn`. The paper says it uses "the
first two bound states in the heavy hole and conduction bands" and that two
bound states were guaranteed. **16E and the paper were therefore not applying the
same state selection**, however close the energies looked. `bound_state_gate()`
reads the per-state table Demo 11 already writes and names *which* state fails
and why — because "domain too short", "outer barrier too thin" and "genuinely
quasi-bound" are different defects with different fixes, and a count cannot tell
them apart.

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

## Commands

Runs anywhere, no licence:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --audit
```

**The variant ladder needs no new solve** — a completed Demo 16E run already
contains `case_02`'s envelopes:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --from-run <16E_run_dir> --case case_02
```

What licensed work remains, and the exact settings each piece needs:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --plan
```

Outer-domain convergence, once the three solves exist:

```bash
python nextnano/demos/16F_paper_absolute_chi2_reproduction_audit/run_demo16f.py --converge 18.2=<run1> 25=<run2> 35=<run3>
```

## Expected outcome, stated in advance

N_z (×2) and the zincblende zone edge together are worth roughly ×8 on the
off-resonant baseline and less at the peak, because the peak contribution goes
as `dk/k` and grows only logarithmically with k_max. **That will not turn 31 pm/V
into 2340 pm/V, and it is not supposed to.** What it does is remove two known
ambiguities honestly, so that the remaining discrepancy is narrowed from "maybe
any of our quantum-well physics is wrong" to a specific short list:

* the factor of 3 between Eq. 1 and Eq. 2 as printed (measured, above);
* the heavy-hole m_j multiplicity the paper does not state (×2 if it applies);
* whatever the bound-state gate turns up once it is strict.

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
