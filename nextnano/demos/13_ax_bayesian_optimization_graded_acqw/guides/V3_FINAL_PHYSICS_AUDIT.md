# v3 final physics audit — Agent 2 (independent)

**VERDICT: FAIL.** Not of the campaign's plumbing, which is sound, but of the
previous physics audit's central claim and of four defects it did not catch.

An independent reviewer re-derived everything from the campaign's own ledger,
trial records and regenerated tables. `V3_PHYSICS_AUDIT.md` (the earlier,
superseded document) claimed *"No physically wrong statement survives in the
code or the regenerated reports."* **That claim is false.**

Findings below marked ✅ were **re-verified directly against the v3 trial
records** during this pass. Findings marked ⬜ are reported as raised and are
**not yet independently confirmed**.

---

## Confirmed defects in code

### ✅ P1 — the optical sign convention was inverted on all 16 trials — FIXED

`metrics13.py` labelled `signed_detuning < 0` as `red_of_target`. Since
`signed_detuning = peak_wavelength − target`, a negative value is a *shorter*
wavelength, which is **blue**-shifted.

Verified against the ledger: every v3 peak lies at **1485–1540 nm**, all short
of 1550 nm, and every record carries `detuning_side: "red_of_target"`.

| Trial | Peak (nm) | Signed detuning | Was labelled | Actually |
|---|---:|---:|---|---|
| t0001 | 1510 | −40 | red_of_target | **blue** |
| t0021 | 1537 | −13 | red_of_target | **blue** |

**Fixed** in this pass. Test: `test_a_peak_below_the_target_is_blue_not_red`.
Every report that described t0021 as detuned "to the red" inherited the error.

### ✅ P2 — the heavy-hole anticrossing gap reported the largest spacing — FIXED

`heavy_hole_anticrossing_gap_meV` promised "the smallest adjacent-level
spacing" but computed `min()` over *signed* gaps. Hole energies decrease with
index, so all gaps are negative and `min` returns the **most negative**, i.e.
the largest separation.

Verified:

| Trial | Reported | All spacings (meV) | True minimum |
|---|---:|---|---:|
| t0005 | −56.36 | 30.98, **4.06**, 56.36 | **4.06** |
| t0021 | −53.89 | 29.45, **7.11**, 53.89 | **7.11** |

This matters: 4–7 meV is **at or inside the 5 meV broadening**. The one
diagnostic that would have surfaced a heavy-hole near-degeneracy was reporting
its opposite, on every trial. **Fixed**; test
`test_the_hole_anticrossing_gap_is_the_smallest_spacing`.

### ✅ P3 — the state tracker is fed fabricated hole energies — NOT FIXED

`tracking13.py:279` sets `hole_energies = np.arange(len(hole_columns))`
unconditionally, discarding the real `heavy_hole_energies_eV` which are present
in every trial record. With reference and current both `[0,1,2,3]`, the energy
tie-breaker is exactly zero on the diagonal and positive off it — so it
**actively rewards the identity assignment**, the precise bias that would hide a
hole-state swap. And per P2 the holes are where the near-degeneracy is.

`state_tracking_confidence` is the minimum over both bands, so the reported
0.993439 for t0021 is partly produced by a band that cannot disagree.

**Not fixed in this pass.** Requires re-tracking with true hole energies, which
needs the stored envelopes.

---

## Confirmed errors in the previous audit's physics

### ✅ P4 — "thin barrier ⇒ near-degenerate doublet" is backwards

The earlier audit, the Stage 5 plan and the registry all argued that the
thinnest barrier maximises tunnel coupling *and therefore* makes the lowest two
electron states most nearly degenerate. Stronger coupling **increases** the
splitting: `E₂−E₁ = √(Δ² + 4t²) ≥ Δ`.

Verified against the records:

| Trial | Barrier (nm) | E₁₂ (meV) |
|---|---:|---:|
| **t0021** | **0.85** (thinnest) | **95.1** |
| t0009 | 1.389 | 94.1 |
| t0018 | 1.136 | **91.4** (smallest) |

The thinnest barrier has one of the *largest* splittings. Nothing in the
electron doublet is near-degenerate — 91 meV is ~18× the 5 meV broadening. The
named "highest risk" for state tracking **does not exist**, and it is currently
a validation priority in `demo_registry.yaml` driving Stage 5 §E.

### ✅ P5 — boundary probability is NOT constant, and its Sobol indices are NOT NaN

The earlier audit recommended moving `maximum_boundary_probability` to
`never_model` because it was "nearly constant" with "NaN" sensitivity indices.
Both are false for v3:

- range **1.78e-5 → 1.91e-3**, a factor of **107**;
- **t0006 violates the 1e-3 bound at 1.91e-3** — a genuine constraint catch,
  and the one design with 4 bound states;
- `bo_parameter_importance` reports finite indices for it, including the largest
  single index in the table.

**Acting on that recommendation would have removed the only constraint that
caught a quasi-bound design.** The recommendation is withdrawn.

---

## Findings reported and not yet independently confirmed

⬜ **P6 — interdiffusion.** A 0.85 nm barrier sits *inside* the 0.3–1 nm
interdiffusion range used to rule out thinner layers, so the argument is
self-contradictory. Estimated peak barrier height retained: 84 % at σ = 0.3 nm,
60 % at σ = 0.5 nm — and the effect is strongly barrier-dependent, acting in
exactly the direction the optimizer is driving.

⬜ **P7 — "3 monolayers" is post-hoc.** `central_barrier_thickness_nm` is
searched as a *continuous* range and the campaign evaluated 3.5–8.3 ML; grade
widths snap to a **mesh** increment, never a lattice one. If monolayer
discreteness were a design constraint it would constrain the parameter.

⬜ **P8 — the objective cannot be monotone in barrier thickness.** At `b → 0`
the two wells merge into one symmetric well, for which χ⁽²⁾ vanishes by parity.
So there is an interior maximum, at 1–3 ML, where neither the continuum barrier
nor the abrupt-interface model is meaningful. The correct statement is not "the
optimum is at or below 0.85 nm" but *the objective is non-monotonic and its
maximum lies where this model cannot represent it.*

⬜ **P9 — the constraint opposes the objective.** Designs further off target
score *higher* at 1550 nm (corr(|Δ|, χ²) ≈ +0.26). The best objective in the
campaign is t0008 at 0.9288 with |Δ| = 34 nm. The constrained optimum therefore
sits *on* the boundary by construction — a boundary being traced, not a maximum
being found.

⬜ **P10 — the ranking turns on one grid point.** The peak is found by bare
`argmax` on a 1.0 nm grid. t0017 is feasible at |Δ| = **exactly 15.0**; t0022
fails at **16.0** with χ² = 0.7467, **82 % higher than the declared winner**. A
sub-nanometre shift flips the answer.

⬜ **P11 — grading is confounded by construction, not merely underpowered.** A
grade needs `fraction × (barrier − 0.10) ≥ 0.80`, so **33 % of the graded branch
is geometrically unbuildable**, entirely at thin barriers. Measured: graded
trials mean barrier 1.815 nm vs abrupt 1.310 nm; mean |detuning| 38.2 vs
23.4 nm. "Five graded designs, none feasible" is predicted by geometry alone.
**And at t0021 the maximum feasible grade is 0.75 nm — below the 0.80 nm
minimum — so no graded variant of the best design exists in this search space.**

⬜ **P12 — the naive read leans the other way.** Graded mean χ² 0.4159 vs
abrupt 0.3951; the closest matched pair (t0008 erf vs t0020 abrupt) gives the
graded design **2.6×** the objective.

⬜ **P13 — the inherited Demo 11 failure exceeds both the constraint and the
objective range.** The registry records that 2 → 3 states per band moves the
resonance **58 nm** and changes peak magnitude **20×**. Demo 13 runs at
`max_states_per_band: 2`. The 58 nm window error is **3.9× the ±15 nm
constraint** that decided every feasibility verdict; the 20× magnitude error
exceeds the campaign's entire 17.4× objective spread. **t0021 (s = 0.3876) and
t0022 (s = 0.4019) straddle the documented artifact cliff at s = 0.39 → 0.40.**

If P13 holds, **no ordering in this campaign — including t0021 over t0022 — is
resolvable against its own systematic error**, and state-count convergence, not
mesh, is the true first gate.

---

## Consequences

1. **t0021 is not a validated optimum, and the gap is wider than previously
   stated.** It is the best design found under a threshold whose position is
   below the inherited systematic error.
2. **Stage 5's ordering is wrong.** State-count convergence should precede the
   mesh gate.
3. **Stage 5 §E targets a risk that does not exist** (P4) while the real
   near-degeneracy (P2/P3, holes at 4–7 meV) is untested.
4. **`maximum_boundary_probability` must stay a modelled constraint** (P5).

## Verdict

**FAIL.** Two code defects fixed (P1, P2); one identified and not fixed (P3);
two claims in the previous audit falsified (P4, P5). Eight further findings
(P6–P13) are recorded as raised and unconfirmed. The plumbing and accounting
remain correct and are unaffected.
