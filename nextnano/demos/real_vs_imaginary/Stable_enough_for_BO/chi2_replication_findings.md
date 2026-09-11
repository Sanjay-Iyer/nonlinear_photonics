# Reproducing the simulated χ⁽²⁾ spectrum of *Enhanced Interband Coupled Quantum Wells*

**Status:** Fig. 2d is reproduced to within 8% in amplitude and 1% in peak position.
Doing so required four choices that are not stated in the paper, one of which changes
the absolute scale by a factor of 39.5. This memo records what was needed and why, so
that the discrepancies can be checked against the original implementation.

Two standalone scripts accompany this memo, one per calculation; see §9.

It then separates two questions. §4–§5 cover **what the paper computed**. §6 gives a
**corrected 8-band k·p calculation** of what the structure does, which we would use for
design work in preference to either. §6.1 records where our inferences are not uniquely
determined by the published figure.

---

## 1. Summary

We set out to reproduce the simulated χ⁽²⁾ curve in Fig. 2d from the description in
the paper's Methods, in order to reuse the model for structure design. The structural
and spectroscopic inputs matched immediately. The absolute magnitude did not: following
the Methods and Eq. 2 literally gives roughly 20 pm/V where Fig. 2d peaks near
3950 pm/V, a factor of about 200.

The gap resolves into four separate items, listed in §4. Applying all four reproduces
the published curve closely, including the near-zero troughs, which no single
adjustment accounts for. Three of the four are normalization or presentation
conventions rather than physics. The remaining one, a missing Brillouin-zone density
of states, means the published χ⁽²⁾ values appear to be high by (2π)² ≈ 39.5 — though
see §6.1, where we show the split between that factor and the prefactor is not uniquely
determined by the figure. That the factor is *absent* is robust; that it is exactly
(2π)² depends on the single-band reading.

§6 separates two questions that want different settings: what the paper computed, which
§4 answers, and what the structure actually does, which we estimate with a corrected
8-band k·p calculation. The second gives ≈262 pm/V at 1550 nm against the published
2340. The two calculations differ by ≈10× rather than 39.5×, because 8-band
non-parabolicity recovers 3.8× of the normalization difference.

Each is a standalone script — `1_band_paper_replication_v1.py` and
`8_band_non_parabolic_v24.py` — listed in §9.

We would welcome correction on any of this — in particular, all four inferences are
drawn from the figure and text alone, without sight of the original code.

---

## 2. What matched without adjustment

Everything in the structural and spectroscopic description reproduced directly.

| Quantity | Paper | This work |
|---|---|---|
| Layer stack | 2.9 / 1.8 / 7.1 nm, 30 nm period | same |
| Al fraction | 0.55 | same |
| Interfaces | abrupt (stated for the 2340 pm/V prediction) | same |
| Broadening Γ | 5 meV | same |
| States retained | first two CB and two HH | same |
| k integration | zone centre to one-tenth of the Brillouin zone | same range; the cutoff value itself is the one exception, see §4.4 |
| e1–h1 | 1.49 eV | 1.4933 eV |
| e2–h2 | 1.62 eV | 1.6367 eV |

The transition energies confirm the band model. The Methods state the envelopes came
from "Schrodinger-Poisson methods with the Nextnano software", i.e. single band. We
initially used an 8-band k·p solver and obtained 1.4979 and 1.6574 eV. Repeating with
a single-band solver gives 1.4933 and 1.6367 eV, closer to the quoted values on both
transitions. The designed structure is undoped, so Poisson contributes no space charge
and the calculation reduces to a 1D BenDaniel–Duke eigenproblem.

Note this cuts against intuition: the more sophisticated 8-band treatment agrees with
the paper *less* well, because it is describing a different physical model rather than
a refinement of the same one.

---

## 3. What did not match

Using single-band envelopes and Eq. 2 exactly as printed, with a textbook conversion
of the in-plane k sum to an integral, we obtain peaks of 7, 13, 19 and 20 pm/V at
500, 757, 1001 and 1513 nm. Fig. 2d shows 1260, 2450, 3250 and 3950 pm/V at
540, 760, 1080 and 1520 nm.

Peak *positions* were therefore close from the outset; only the two artefact peaks
(§4.4) were displaced. The amplitude was low by a factor of roughly 200, which is far
outside any plausible tolerance on material parameters.

---

## 4. The four items

### 4.1 The factor of 1/6 in Eq. 2

Eq. 2 carries a prefactor `N_z e³ r_e,hh² / 6 ε₀ ħ²`. Reproducing Fig. 2d requires a
prefactor **6× larger than this**, i.e. the `1/6` absent.

We are not able to say what the 6 should be replaced by from first principles, because
the correct constant depends on permutation-symmetry factors that are entangled with
how the term list in Eq. 2 is enumerated, and we did not re-derive those. What we can
say is empirical: with the `1/6` present, Fig. 2d cannot be reproduced under any of the
other choices in this memo; with it absent, it can.

One internal observation supports treating the 6 as suspect. Eq. 1, the general form in
the same Methods section, carries `1/2 ε₀ ħ²`, and the 6 appears only after the
simplification to Eq. 2. The stated simplifications — restricting to χ_xzx, pulling
r_e,hh out of the sum, setting the Fermi factor to unity, and truncating to two states
per band — do not obviously produce a factor of 3. This is consistent with a
transcription slip between implementation and manuscript rather than an error in the
calculation itself, but we cannot confirm that from outside.

### 4.2 The Brillouin-zone density of states

This is the substantive one. Converting the in-plane sum to an integral in 2D carries
the density of states,

```
(1/A) Σ_k∥  =  g_s/(2π)² ∫d²k  =  (1/π) ∫k dk        [spin degeneracy g_s = 2]
```

Reproducing Fig. 2d requires instead

```
Σ_k∥  →  g_s ∫d²k  =  4π ∫k dk
```

which is larger by exactly (2π)² = 39.478. The Methods describe this step in words —
"the summation over in-plane k states was converted to an integral over (kx, ky)" —
without giving the measure, so we cannot check it against the text.

The 1/(2π)² is required, not conventional; it is what makes the result a density.
**If this reading is right, the χ⁽²⁾ values in Fig. 2d and the 2340 pm/V figure quoted
at 1550 nm are high by ≈39.5×.** We flag it as the item most worth checking against the
original code, since it is the one with consequences beyond reproducing the figure.

Note the factor required is numerically (2π)², not an arbitrary constant. That is what
led us to this interpretation rather than to a fitted fudge factor.

### 4.3 The plotted quantity has no imaginary part

Fig. 2d touches zero at approximately 605 and 1330 nm. A magnitude |χ⁽²⁾| cannot do
this unless Re and Im vanish together. In our calculation the value at those two
wavelengths is 99% and 100% imaginary respectively, so |χ⁽²⁾| has no zeros anywhere —
it dips only to 1400 and 3060 pm/V.

The reason is the k continuum. With E(k∥) sweeping from 1.49 to 2.33 eV across the
integration range, some k state is exactly resonant at *every* fundamental wavelength
in 531–830 nm and 1062–1661 nm. Both troughs lie inside those windows, so the
absorptive part cannot vanish there. Only Re passes through zero, where neighbouring
resonances interfere destructively.

Taking |Re χ⁽²⁾| puts the zeros at 616 and 1343 nm, within 2% and 1% of the figure,
and simultaneously improves the peak heights (§5). Two readings are consistent with
this and we cannot distinguish them from the figure:

1. Re χ⁽²⁾ was plotted, and the absolute-value bars on the axis label are a slip.
2. The computed χ⁽²⁾ was real-valued — for instance if the `+iΓ` terms were not carried
   as complex arithmetic — in which case the axis label is correct and the difference
   lies upstream.

The axis is labelled "Simulated |χ⁽²⁾| (pm/V)" with explicit bars, and the words "real
part" and "imaginary" do not appear in the paper. Reading 2 seems at least as likely as
reading 1 and implies no labelling error.

Scope note: this item identifies the *plotted quantity*, not the band model. Repeating
the exercise with 8-band envelopes puts the zeros at 611 and 1310 nm, comparable to the
single-band 586 and 1321. Both models reproduce the troughs, because the zeros arise
from interference between the same two resonances. The trough structure should
therefore not be read as evidence for §2's single-band conclusion, which rests on the
transition energies instead.

### 4.4 The k-space cutoff is 1.0 nm⁻¹, not one-tenth of the zone

Two of the four peaks — 540 and 1080 nm — are not transitions. They are the ω and 2ω
images of the edge left by truncating the k integral, which places a resonance at
E(k_max) = E(0) + ħ²k_max²/2μ. The other two, 760 and 1520 nm, are the genuine e2–h2
resonance and sit at E(0).

One-tenth of the GaAs Brillouin zone is 2π/a = 1.1114 nm⁻¹, which puts the artefacts at
500 and 1001 nm. A cutoff of **1.000 nm⁻¹** puts them at 535 and 1071 nm, aligning all
four peaks to better than 1%. We checked the in-plane hole mass as an alternative knob
and it is far too weak: varying m_hh from 0.34 to 0.60 moves the artefact by only 2%.

The round value suggests 1.0 nm⁻¹ was used as a stand-in for one-tenth of the zone.

A consequence worth noting independently of the above: because two of the four peaks
are truncation artefacts, they are *not* physical resonances, and their position
depends on an integration parameter rather than on the structure. The paper's text
attributes only the 760 and 1520 nm peaks to transitions, which is consistent, but the
540 and 1080 nm features should probably not be read as spectroscopic predictions. The
Methods state that the k contribution "saturated by one-tenth of the Brillouin zone";
in our reproduction it has not saturated, which is precisely why the artefacts appear.

---

## 5. Result

With all four items applied — single-band envelopes, no 1/6, unnormalized k sum, real
part, cutoff 1.000 nm⁻¹ — as implemented in `1_band_paper_replication_v1.py`:

| Feature | Fig. 2d | This work | Ratio |
|---|---|---|---|
| Amplitude at 540 nm | 1260 pm/V | 1162 pm/V | 0.92 |
| Amplitude at 760 nm | 2450 pm/V | 2567 pm/V | 1.05 |
| Amplitude at 1080 nm | 3250 pm/V | 3333 pm/V | 1.03 |
| Amplitude at 1520 nm | 3950 pm/V | 3859 pm/V | 0.98 |
| Peak positions | 540 / 760 / 1080 / 1520 nm | 535 / 758 / 1070 / 1515 nm | within 1% |
| Trough 1 | ~605 nm, ~0 | 616 nm, 2 pm/V | — |
| Trough 2 | ~1330 nm, ~0 | 1343 nm, 0 pm/V | — |
| At 1550 nm | 2340 pm/V (quoted in text) | 2717 pm/V | 1.16 |

The agreement at 1550 nm is an independent check, since that value is quoted in the
body text rather than read off the figure.

Amplitudes are compared at the paper's peak wavelengths rather than at ours, because
the two artefact peaks are truncation edges and therefore very sharp: their apparent
height depends on how finely the wavelength axis samples them. Sampling at 1200 points
over 400–1850 nm puts the 1070 nm maximum at 4203 pm/V and at 900 points at 3309 pm/V,
a 27% spread that says nothing about the physics. The genuine resonances at 758 and
1515 nm are broadened by in-plane dispersion and are stable to a few percent.

Applying the correct 1/(2π)² and leaving everything else unchanged gives **69 pm/V at
1550 nm** and 98 pm/V at the 1520 nm peak.

---

## 6. Two calculations, two purposes

Everything above answers "what was computed?". That is a different question from "what
does this structure do?", and the two want different settings. They are now two
standalone nextnanopy scripts, each running its own solver and needing nothing from the
other.

**(a) Reproduction — `1_band_paper_replication_v1.py`.** Single-band `Gamma{}`/`HH{}`
envelopes, no 1/6, unnormalized k sum, real part, cutoff 1.000 nm⁻¹. This regenerates
the published curve to within 8% (§5). It exists to establish what was done, and we
would not use it to predict anything. The four conventions are isolated in one block at
the top of the file with the evidence for each, so they can be toggled individually.

**(b) Corrected calculation — `8_band_non_parabolic_v24.py`.** 8-band k·p dispersion,
correct 1/(2π)² density of states, magnitude rather than real part, cutoff at
one-tenth of the zone as the Methods describe. This is our best estimate of the actual
response:

| Feature | λ | \|χ⁽²⁾\| | Interpretation |
|---|---|---|---|
| e2–h2 at 2ω | 1494 nm | 563 pm/V | resonance |
| e2–h2 at ω | 749 nm | 342 pm/V | resonance |
| — | 1134 nm | 631 pm/V | k-cutoff artefact |
| — | 567 nm | 271 pm/V | k-cutoff artefact |
| at 1550 nm | — | 262 pm/V | — |

Only the 749 and 1494 nm features are resonances. The other two are the truncation edge
of §4.4 and should not be read as predictions; they move if the cutoff moves.

The script demonstrates this rather than asserting it. It re-runs the whole integral
with the cutoff reduced to 92% and matches the peaks between the two runs: the 567 and
1134 nm features shift by +22 and +40 nm, while 749 and 1494 nm do not move at all.
That test runs on every invocation, so the classification cannot silently go stale if
the structure or the cutoff changes.

Why 8-band matters here rather than being ornamental: conduction-band non-parabolicity
means e1–h1 reaches only 1.977 eV at the cutoff, where the parabolic single-band model
reaches 2.334 eV. The 8-band bands are *stiffer* in the sense that matters — less
energy sweep across the integration range — so the k integral smears the resonance
less and χ⁽²⁾ comes out 3.8× higher than single-band under identical normalization.

**The two curves differ by ≈10×, not by 39.5×.** The (2π)² applies at fixed band model;
going from (a) to (b) also swaps parabolic for 8-band dispersion, which recovers 3.8×
of it. Net: 39.5 / 3.8 ≈ 10, and directly 2717 / 262 = 10.4.

### 6.1 The fit is not unique

We should record a degeneracy we found while checking (b). Our four items are one
self-consistent solution, not the only one. Running 8-band under the paper's
conventions overshoots Fig. 2d by 5.4–8.0×, averaging about 6.6 — close enough to 6
that **keeping the 1/6 of Eq. 2 and dropping only the 1/(2π)²** brings 8-band within
roughly 33% of the published curve.

That is a worse fit than single-band's 6%, and three independent observations still
favour single-band: it matches the quoted 1.49/1.62 eV more closely, it puts the
genuine resonance at 757/1513 nm against the paper's 760/1520 where 8-band gives
748/1495, and it produces exactly two near-zero troughs where 8-band produces three.
Combined with the Methods explicitly stating Schrödinger-Poisson, we present
single-band as the primary reading.

But the honest position is that §4.1 and §4.2 are correlated: the *product* of
prefactor and k measure is what the figure constrains, and separating them relies on
the band model being single-band. What survives both readings is that **the 1/(2π)² is
absent** — no combination we found reproduces Fig. 2d while retaining it. That is the
load-bearing claim. Identifying the factor as *exactly* (2π)² rather than ~6.6 is
contingent on the single-band reading.

---

## 7. Open question

The corrected magnitude sits uncomfortably against the measurement. The paper reports
χ⁽²⁾_eff ≈ 1345 pm/V for the growth-interrupted sample at 1550 nm. Against the
corrected 8-band calculation of §6(b), 262 pm/V at 1550 nm, the measurement is **5.1×
higher**; against the corrected single-band value of 69 pm/V it is 20× higher. Against
the published simulation it is 1.7× *lower*.

The better the band model, the smaller this gap becomes — 8-band closes it from 20× to
5.1× — which is at least the right direction, and leaves the residual within reach of
the assumptions below rather than requiring something structural.

This runs opposite to the normalization discrepancy and is not explained by anything
above. Possible directions, none of which we have tested:

- the measured χ⁽²⁾_eff includes field-enhancement or propagation factors not present
  in the bulk-susceptibility calculation;
- N_z, taken here as one well per 30 nm period, is defined differently in the original;
- the unit-cell interband matrix element r_e,hh (7.51 Å here) differs.

We note the citing paper (*Quantum Well Metasurface to Maximize Nonlinear
Polarization*) labels N_z as a spin degeneracy rather than a sheet density, which
suggests this definition may be a recurring source of confusion.

Until this is settled we would treat the absolute scale as unresolved in both
directions. Relative comparisons between structures, and all peak positions, are
unaffected by every item in §4 except §4.4.

---

## 8. Notes on running the model

Independent of the above, three points cost us time and may be useful to anyone
rebuilding this calculation.

**k-grid resolution dominates the answer.** χ⁽²⁾ integrates to ~1.1 nm⁻¹, but a solver
grid reaching 2.3 nm⁻¹ leaves only 5 of 15 shells inside the cutoff, and the discarded
shells still bias the dispersion fit. Worse, E(k) then rises 78 meV — 16 linewidths at
Γ = 5 meV — between k = 0 and the first sampled shell, so the entire resonance is
crossed in an unsampled interval. Peak heights then came from the interpolant, not the
data: changing only the polynomial degree moved a peak by 3.2×. Matching the solver
range to the integration range and refining fixed this; with 40 shells inside the
cutoff the same test varies by ~10%.

**Fit the dispersion in k², not k.** E(k∥) must be even in k. An unconstrained
polynomial fit introduces a linear term at zone centre — about 0.07 eV·nm in our case
— which detunes the transition by ~6 meV across the resonant disc |k| < 0.086 nm⁻¹.
That exceeds Γ, so resonances were being damped by the choice of fit basis.

**Only a very small part of k space matters.** With Γ = 5 meV the resonant region is
|k| < 0.086 nm⁻¹, under 1% of the integration area. Accuracy there matters far more
than the extent of the grid.

We also note that shell-averaging E over |k| is lossy: in-plane warping gives the
heavy-hole branch a 26.5 meV spread at |k| = 0.755 nm⁻¹, about five linewidths, so
E(|k|) is not single-valued and no smooth curve fits it better than ~20 meV. This did
not materially affect our results but bounds how well this class of model can do.

Two nextnano++ output conventions are worth flagging because both fail silently:

- **The default wavefunction files are offset for plotting.** `wf_amplitudes_shift_*`
  has each ψ shifted vertically by its own eigenvalue so the states stack nicely on a
  band diagram. Reading those as wavefunctions corrupts every overlap and dipole while
  still producing plausible-looking numbers. Request `energy_shift = both` and read the
  unshifted file, or subtract the eigenvalues back off.
- **The HH solver's energy zero is not guaranteed to be the Γ solver's.** Eigenvalues
  may come back either on a common absolute scale or as positive confinement depths
  below the valence edge, and the sign also flips which eigenvalue is the hole ground
  state. Here the hole confinement is only 14 meV, so *both* readings put e1–h1 within
  30 meV of 1.49 eV and a single transition cannot distinguish them. The pair can: the
  e1–h1 to e2–h2 splitting is 0.13 eV and comes out with the wrong sign under the wrong
  hypothesis. `resolve_hole_scale()` in the single-band script tests both and prints
  the margin rather than assuming one.

---

## 9. Reproducing this

Two self-contained scripts carry the conclusions. Each drives nextnano++ itself, reads
back its own output, and computes χ⁽²⁾; neither imports the other or any helper below.

| Script | Purpose |
|---|---|
| `1_band_paper_replication_v1.py` | §4–§5. Single-band deck, the four conventions, reproduction of Fig. 2d |
| `8_band_non_parabolic_v24.py` | §6(b). 8-band k·p deck, corrected normalization, artefact classification |

The rest are the diagnostics the conclusions were derived from, kept for audit. They
are not needed to run either script.

| File | Purpose |
|---|---|
| `single_band_model.py` | Standalone BenDaniel–Duke solver; cross-checks the nextnano single-band envelopes |
| `reconcile_prefactor.py` | Tests the prefactor and k-measure conventions against all four peaks (§4.1, §4.2) |
| `check_troughs.py`, `check_real_part.py` | Establishes that the plotted quantity has no imaginary part (§4.3) |
| `align_peaks.py` | Scans cutoff and hole mass; identifies 1.0 nm⁻¹ (§4.4) |
| `plot_aligned.py` | Reproduction overlay (`chi2_aligned.png`) |
| `plot_two_situations.py` | §6 figure (`chi2_two_situations.png`) |
| `final_numbers.py` | Regenerates the numbers quoted above |
| `benchmark_absorptance.py` | Checks the k measure and r_e,hh against πα absorptance quantization |
| `check_k_convergence.py`, `check_even_fit.py`, `check_dispersion_fit.py` | The §8 diagnostics |
| `8_band_non_parabolic_v23.py` | Predecessor of v24; retained only for diff |

Assumed inputs: Γ = 5 meV, N_z = 1/(30 nm), r_e,hh = 7.51 Å, T = 300 K,
Q_c = 0.65, m_e = 0.067, m_hh = 0.34, E_g(GaAs) = 1.424 eV.
Transition energies are insensitive to Q_c: varying it over 0.60–0.70 moves e1–h1 by
under 2 meV and e2–h2 by 7 meV.
