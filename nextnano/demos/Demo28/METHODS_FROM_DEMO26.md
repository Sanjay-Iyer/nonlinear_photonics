# Archived methods from Demo26_Condensed

This is the source package's historical documentation, retained for methodological
context. Use README.md for Demo 28 commands, scope and current validation. Historical
test counts in this document have not been adopted as Demo 28 test results. The
phrase "self-consistent 8-band calculation" below means internally matched inputs;
the deck runs quantum only and does not solve a self-consistent Poisson loop.
All methods remain approximations; "production" names a code mode, not independent
validation of a complete multiband optical-response theory.

A self-contained package that reproduces the Demo 26 investigation of the simulated
second-order susceptibility in Figure 2d of *Enhanced Interband Optical Nonlinearities
from Coupled Quantum Wells* (arXiv:2602.23246). It needs nothing from the rest of this
repository.

```text
01_run_nextnano.py    nextnano++ Professional: electronic structure  ->  raw results
02_calculate_chi2.py  Python: raw results -> Equation 2 -> complex χ² -> plots, CSV, validation
```

---

## 1. What this reproduces

Figure 2d shows a simulated χ⁽²⁾ spectrum for a GaAs/Al₀.₅₅Ga₀.₄₅As asymmetric coupled
quantum well, plotted against the fundamental (input) wavelength. Its axis says |χ⁽²⁾|,
but the curve touches zero twice. The Demo 26 work found that the published curve behaves
much more like **|Re χ⁽²⁾|** than like the complex magnitude **|χ⁽²⁾|**. This package
recomputes χ⁽²⁾ from nextnano output, keeps it complex until the very end, and tests that
reading numerically instead of assuming it.

## 2. The two scripts

**`01_run_nextnano.py`** builds the nextnano++ input decks, checks them, and runs them on
a machine with nextnano++ Professional. It writes one folder per calculation plus a
metadata file recording exactly what was run. `--preflight` and `--dry-run` do everything
except launch the solver.

**`02_calculate_chi2.py`** reads those folders and identifies the electron and hole
states. It computes overlaps and position matrix elements, then evaluates Equation 2 over
in-plane k. It writes Re χ², Im χ², |Re χ²| and |χ²| as plots and CSV files, adds a
comparison against Figure 2d, and produces a PASS / FAIL / NOT APPLICABLE validation table.

## 3. Home laptop (no nextnano): run it now

Python 3.10+ with the packages in `requirements.txt`.

```bash
python -m pip install -r requirements.txt
```
```bash
python 02_calculate_chi2.py --input cached_raw --check-reference
```
```bash
python 01_run_nextnano.py --preflight
```
```bash
python -m pytest tests
```

`cached_raw/` is real nextnano++ Professional output shipped with the package (about
3 MB; see `cached_raw/PROVENANCE.md`). Without `--input`, Script 2 uses `output/raw` if
Script 1 has produced results there. Otherwise it falls back to `cached_raw` and says so.
`--check-reference` makes Script 2 exit with code 3 if any applicable validation check
fails.

## 4. Work laptop with nextnano++ Professional

Tell Script 1 where nextnano is, by flags, environment variables or a machine file:

```bash
python 01_run_nextnano.py --preflight --exe "<path>/nextnano++_Intel_64bit.exe" --database "<path>/database.nnp" --license "<path>/License_nnp.lic"
```
```bash
python 01_run_nextnano.py --run --exe "<path>/nextnano++_Intel_64bit.exe" --database "<path>/database.nnp" --license "<path>/License_nnp.lic" --output results/demo26_run1
```
```bash
python 02_calculate_chi2.py --input results/demo26_run1 --output results/demo26_run1_analysis --check-reference
```

Equivalent: set `NEXTNANO_EXE`, `NEXTNANO_DATABASE`, `NEXTNANO_LICENSE`, or pass
`--machine nextnano_machine.work.yaml` (flat `executable:`, `database:`, `license:`,
`threads:` keys).

`--run` refuses before writing anything in any of these cases:
* any of the three files is missing
* the executable is a Free build
* the output folder already holds job results or a `demo26_run_metadata.json`

A job that exceeds `--timeout` (default 14400 s) is recorded as FAIL. Expect about
10 minutes for the kp8 deck and seconds for the two single-band decks.

Useful Script 1 options (defaults reproduce the Demo 26 dataset):

| option | effect |
|---|---|
| `--jobs kp8` | run only the production 8-band deck (skip the historical single-band decks) |
| `--k-max-per-nm 1.11142887846 --k-points 601` | extend the dispersion to 0.1·2π/a at the same k spacing (the Demo 27G deck) |
| `--interface abrupt` | the paper's abrupt interfaces instead of 1 nm grading (the Demo 27D deck) |
| `--threads N`, `--timeout S` | solver threads; per-job wall-clock limit |
| `--parser-exe`, `--parser-database` | nextnano++ build used for the `--parse` grammar check (a Free build is fine) |
| `--dry-run` | also write the decks and exact commands into the output folder |

The command issued per deck is
`<exe> -d <database> -l <license> --threads N -o <output>/<job> <output>/decks/<job>.in`.

## 5. What nextnano calculates

The production deck (`decks/kp8_dispersion.in`) is a one-dimensional **8-band k·p**
calculation. nextnano solves the Schrödinger equation along the growth direction for the
coupled conduction, heavy-hole, light-hole and split-off bands. All band parameters come
from its material database.

| setting | value |
|---|---|
| structure | Al₀.₅₅Ga₀.₄₅As barriers; GaAs wells 9.1–16.2 nm (7.1 nm) and 18.0–20.9 nm (2.9 nm); 1.8 nm tunnel barrier; 30 nm period |
| interfaces | 1 nm linear composition grading at all four interfaces (`--interface abrupt` available) |
| temperature, substrate, growth | 300 K, GaAs, [100] (nextnano's x axis = the physics z axis) |
| mesh | 0.05 nm at the interfaces, 0.5 nm at the outer ends |
| quantum region | x = 7.1–22.9 nm, Dirichlet boundaries, `no_density = yes`, no Poisson loop |
| states | 6 electron + 8 hole = 14 states (7 Kramers doublets) |
| in-plane k | dispersion path from Γ toward [010], 301 points, 0 to 0.555714439232 nm⁻¹ = 0.1·π/a |
| exported | E_n(k∥) for all 14 states; k=0 spinor envelopes, spinor composition and kp8 dipole matrix elements |

From that run the package takes **energies E_n(k∥), k=0 envelope wavefunctions, band
character, and nextnano's own dipole matrix elements** (used as a cross-check).

Two small **single-band** decks (`decks/singleband_*.in`) exist only to reproduce the
historical Demo 26 calculation, which mixed single-band matrix elements with the kp8
dispersion. They are not part of the production path.

## 6. What Python calculates

```text
nextnano raw results
  -> Kramers doublets and band character (CB/HH/LH/SO fractions)
  -> choose e1, e2 (conduction) and hh1, hh2 (heavy hole)
  -> one real envelope per doublet (CB block for electrons, HH block for holes)
  -> overlaps O[n,m] and position matrix elements Ze[n,l], Zh[m,l]
  -> spin-split transition energies E_e,n(k∥) - E_hh,m(k∥) for each branch pairing
  -> Equation 2, 16 pathways, complex denominators
  -> integrate over k∥, apply the prefactor, average the four branch pairings
  -> complex χ²(λ)  ->  Re, Im, |Re|, |χ|  ->  paper comparison
```

## 7. The physics, briefly

**E_n(k∥).** Electrons in a quantum well are confined along z but free in the plane.
Each subband n has an energy that depends on the in-plane momentum k∥. At k∥ = 0 the
energies are the familiar quantized levels. Away from zero they curve up (electrons) or
down (holes). A transition is available at every k∥, not just at k∥ = 0.

**Spin splitting.** At k∥ = 0 every level is a Kramers doublet: two states with the same
energy. In this asymmetric well the two members separate as k∥ grows. Here the splitting
reaches 1.6 meV (e1), 2.8 meV (e2), 5.5 meV (hh1) and 11.7 meV (hh2), which is up to 2.3 Γ.

**Overlaps O[n,m] = ⟨e_n|hh_m⟩.** How much the electron envelope and the hole envelope
occupy the same place. Equation 2 factors the atomic-scale (Bloch) part of the optical
matrix element into the constant r_e,hh, so what remains is this envelope overlap.
It cannot be the full 8-band spinor inner product: different kp8 eigenstates are
orthogonal, so that product is zero.

**Position matrix elements Ze[n,l] = ⟨e_n|z|e_l⟩ and Zh[m,l] = ⟨hh_m|z|hh_l⟩.**
Diagonal entries are where each state sits. Off-diagonal entries are the intersubband
dipole lengths. The electron and hole diagonal terms nearly cancel. What survives is the
asymmetry of the structure, which is why a symmetric well has no χ².

**Two-photon denominator** `E_transition − 2ħω + iΓ` becomes small when two photons
together match a transition. **One-photon denominator** `E_transition − ħω + iΓ` becomes
small when one photon does. So each transition energy E gives features at both λ = hc/E
and λ = 2hc/E on the fundamental-wavelength axis.

**Γ = 5 meV** is the broadening. It keeps the denominators finite at resonance and sets
the linewidth.

**Why χ² is complex.** Because the denominators contain iΓ, every term is a complex
number. The real part is the dispersive response, which changes sign across a resonance.
The imaginary part is the resonant (absorptive-like) part. It is large wherever some
k∥ state is resonant.

**Re χ², Im χ², |Re χ²|, |χ²|.** `|χ²| = sqrt(Re² + Im²)` can only be zero where Re and Im
vanish together. `|Re χ²|` is zero wherever Re changes sign, even if Im is large there.
The two are genuinely different curves.

**Finite-k integration.** Contributions from every k∥ are added with the 2D measure
`g_s · k dk / (2π)` (the isotropic form of ∫d²k/(2π)², spin degeneracy g_s = 2), using
trapezoid weights on the nextnano k grid. Stopping the integral at a hard k_max leaves
an endpoint feature at E(0) + ħ²k_max²/2μ, which moves when k_max moves.

## 8. Equation 2 as implemented (`src/equation2.py`)

Indices:
* `n` = electron state of the pair
* `m` = heavy-hole state of the pair
* `ell` = the intermediate state: an electron in conduction pathways, a hole in valence pathways
* `transition[n,m] = E_e,n(k) − E_hh,m(k)`

```text
conduction:  + conj(O[n,m]) · Ze[n,ell] · O[ell,m]  /  [(transition[n,m] − 2ħω + iΓ)(transition[ell,m] − ħω + iΓ)]
valence:     − O[n,m] · Zh[m,ell] · conj(O[n,ell])  /  [(transition[n,m] − 2ħω + iΓ)(transition[n,ell] − ħω + iΓ)]
```

* 2 × 2 × 2 conduction + 2 × 2 × 2 valence = **16 pathways**, all retained.
* The conjugations make the numerators invariant under arbitrary state phases (tested).
  For real matrix elements they reduce exactly to the validated Demo 22 algebra (tested).
* ħω = 1239.841984 / λ[nm] eV, where λ is the **fundamental** wavelength.
* Γ enters as 0.005 eV with `+iΓ`, exactly as Equation 2 is written. With the usual
  e^(−iωt) time convention a causal response has `−iΓ`, so the sign of Im χ² is
  convention-dependent. With `−iΓ`, Im changes sign for real matrix elements, and Re,
  |Re| and |χ| do not change (tested). The kp8 matrix elements are real.
* χ² = prefactor × Σ_k w_k Σ_pathways. The prefactor is `N_z e³ r_e,hh² / (6 ε₀)`, with
  unit conversion, = **56.69816882497043 pm/V per summand** for N_z = 1/(30 nm) and
  r_e,hh = 0.751 nm. This matches the Demo 21 walkthrough exactly.
* The absolute scale is a convention. The paper publishes neither N_z's meaning nor
  r_e,hh, and an independent replication argues its printed 1/6 and the 1/(2π)² should
  both be revisited. Shapes, zeros and ratios do not depend on it.

## 9. Calculation modes

| mode | what it is | inputs |
|---|---|---|
| `kp8` | **Production.** Everything from the one 8-band run: kp8 energies and spin-split dispersion, heavy holes chosen by band character, matrix elements from kp8 envelopes. | `kp8/` |
| `demo26-baseline` | The historical Demo 26 / Demo 23D calculation, reproduced exactly to validate the engine: kp8 dispersion shape shifted onto single-band energies, single-band matrix elements, doublet-averaged energies. | `kp8/`, `singleband_case04_graded/` |
| `demo26-cutoff` | The historical **diagnostic** behind the four-peak match: parabolas fitted to the baseline dispersion, extrapolated in Python to k_max = 0.1·2π/a, with abrupt-case matrix elements. Not production. | adds `singleband_case00_abrupt/` or the supplied JSON |

**How states are chosen in `kp8` mode.**

| doublet | E(k=0) eV | CB | HH | LH | SO | role |
|---|---:|---:|---:|---:|---:|---|
| 13, 14 | 3.0911 | 0.931 | 0 | 0.051 | 0.018 | e2 |
| 11, 12 | 2.9525 | 0.963 | 0 | 0.028 | 0.010 | e1 |
| 9, 10 | 2.3391 | 0.563 | 0 | 0.318 | 0.119 | excluded (mixed, inside the gap) |
| 7, 8 | 2.3391 | 0.563 | 0 | 0.318 | 0.119 | excluded (mixed, inside the gap) |
| 5, 6 | 1.4438 | 0 | 1.000 | 0 | 0 | hh1 |
| 3, 4 | 1.4167 | 0.020 | 0 | 0.976 | 0.005 | excluded (light hole) |
| 1, 2 | 1.3977 | 0 | 1.000 | 0 | 0 | hh2 |

* **Electrons:** the two lowest doublets with ≥ 80% conduction character.
* **Heavy holes:** the two highest doublets with ≥ 80% heavy-hole character.
* **(3,4), the historical "hh2":** the old calculation picked it because its energy
  matched a single-band heavy-hole level, but it is 97.6% light hole. Its envelope
  overlaps hh1's at 0.98 (not orthogonal), and nextnano's own ⟨hh1|z|lh1⟩ is
  2.5×10⁻¹³ nm. It is not a valid Equation 2 heavy-hole state.
* **(7,8) and (9,10):** these sit inside the band gap with mixed character, so the 80%
  rule excludes them and they do not enter χ². Their origin (for example a spurious
  8-band solution or a boundary state) was not investigated.

**Spin-split energies (production).** nextnano exports the two members of each doublet as
separate dispersion columns. The deck exports spinors only at k = 0, so the package cannot
tell which electron branch couples to which hole branch. Production χ² is therefore the
**average of Equation 2 over the four lower/upper electron–hole branch pairings**, using
the same k=0 matrix elements.

As a sensitivity check, the historical doublet-averaged energies were also run:
* χ² changes by at most 12% of its maximum
* the Re zeros move by less than 0.5 nm
* the largest |χ²| becomes 188.6 pm/V at 1332 nm, compared with 175.9 pm/V at 1336 nm

**Branch guard.** Dispersion columns are energy-sorted, not tracked by wavefunction. Over
the whole k range, the closest any selected branch comes to any other column is 11.84 meV
(hh1). That is more than 2Γ. Validation requires this gap to stay ≥ Γ.

**Envelope reduction.** Each Kramers doublet's CB (electron) or HH (hole) components are
reduced to one real function by singular-value decomposition over both doublet members.
The result does not depend on how LAPACK mixes the degenerate pair. The second singular
value and the imaginary residue are zero to machine precision, so the reduction is exact.

Envelopes are renormalized to unit norm within their block, which is the envelope-function
factorization Equation 2 assumes. They are then Löwdin-orthonormalized within each band.
As a sensitivity check, the electron overlaps were weighted by the conduction-block
amplitude (√0.963, √0.931) instead; χ² changes by at most 6.9% of its maximum.

**z-origin test.** Shifting the z origin by 20 nm inside every ⟨|z|⟩ integral changes
production χ² by 2.2×10⁻¹² pm/V. The same shift applied before Löwdin orthonormalization
changes χ² by 2.19 pm/V, because the raw envelopes are not exactly orthogonal. The
invariance is therefore earned by the orthonormal basis, not built into the test.
Separately, adding c·I to Ze and Zh cancels between conduction and valence pathways to
about 10⁻¹² pm/V.

**Cross-checks against nextnano itself.**
* |Zh[hh1,hh2]| = 1.353216 nm, against nextnano's 1.353216 nm (1×10⁻⁷ relative).
* |Ze[e1,e2]| = 1.2932 nm, against nextnano's full-spinor 1.2955 nm. They are 0.17%
  apart because the electrons carry 4–7% non-conduction weight.

nextnano's exported interband momentum matrix elements are envelope-only and vanish for
the e–hh pairs, so they cannot check O. Instead, `tools/build_reference.py` recomputes
|O|, |Ze| and |Zh| from the raw envelope files with separate code: largest single block
component, phase fixed, Löwdin, no SVD. The package agrees with it to 10⁻⁸.

**Supplied, not generated.**
* r_e,hh = 0.751 nm (bulk DFT value), N_z = 1/(30 nm) and Γ = 5 meV are model constants.
* The abrupt case00 matrix elements used by `demo26-cutoff` come from a processed
  historical table, because the raw case00 envelopes were not kept. A fresh Script 1 run
  regenerates them, and Script 2 then prefers the raw run.

## 10. Output files

```text
output/
├── raw/                                  Script 1
│   ├── preflight_manifest.json | dry_run_manifest.json | demo26_run_metadata.json
│   ├── decks/<job>.in                    decks actually issued (dry-run / run)
│   ├── kp8/ ...                          nextnano output per job (run)
│   ├── singleband_case04_graded/ ...
│   └── singleband_case00_abrupt/ ...
└── analysis/                             Script 2
    ├── VALIDATION.md, validation.json    PASS / FAIL / NOT APPLICABLE by category
    ├── run_metadata.json                 input root, SHA-256 of every raw file, config
    └── kp8/ | demo26_baseline/ | demo26_cutoff/
        ├── chi2_spectrum.csv             wavelength_nm, photon_energy_eV, chi2_real/imag/abs_real/abs_pm_per_V, normalized columns
        ├── pathways.csv                  all 16 complex pathway contributions per wavelength
        ├── derived_inputs.json           states, doublet table, energies and branches, O, Ze, Zh, checks
        ├── summary.json, SUMMARY.md      parameters, zeros, peaks, minima, paper metrics, sensitivity, computed finding
        ├── 01_chi2_real.png              signed Re χ² (pm/V), Re zero crossings marked
        ├── 02_chi2_imag.png              signed Im χ² (pm/V), Im marked where Re = 0
        ├── 03_chi2_abs_real.png          |Re χ²| vs paper (each normalized to its own maximum)
        ├── 04_chi2_magnitude.png         |χ²| and |Re χ²| on one absolute axis (pm/V)
        ├── 05_paper_vs_absreal_vs_magnitude.png   paper, |Re χ²|, |χ²| (each normalized to its own maximum)
        ├── 05b_absreal_vs_magnitude_absolute.png  same, absolute: calculation left axis, paper right axis
        ├── 06_real_and_imag.png          Re and Im χ² together (pm/V)
        └── 07_k_cutoff_dependence.png    |Re χ²| for several k cutoffs
```

Normalization is only ever "divide a curve by its own maximum", and only in the plots
labeled "normalized". Signed and absolute plots are in pm/V.

The k-cutoff plot works differently per mode:
* `kp8` and `demo26-baseline`: it truncates the solved k range at 0.05, 0.075 and 0.1·π/a.
* `demo26-cutoff`: it extrapolates parabolas to 0.1, 0.15, 0.2 and 0.25·π/a.

## 11. Validation performed (home laptop)

`validation/reference_demo26.json` is built by `tools/build_reference.py`. Every check has
one of three categories:

| category | meaning | checks |
|---|---|---:|
| `reference` | A value from a file that existed before this package, or raw nextnano output. Sources: the saved Demo 23D spectrum, the saved Demo 26 zero-crossing and metric tables, the prior audit, the saved cutoff diagnostic, Demo 21's prefactor. | 30 |
| `independent_rederivation` | Recomputed from raw nextnano files by code that shares nothing with the package | 3 |
| `consistency` | An invariant that must hold for any dataset (limits only, no dataset values) | 22 |

Where a saved table quotes a number, the builder also recomputes it from the saved
spectrum and requires agreement. No reference value comes from this package's pipeline.

**Other datasets.** Reference and re-derivation values describe this dataset only. The
reference file records the kp8 deck, the case04 deck and the analysis config they came
from. If Script 2 analyses a run whose deck or config differs (for example the k-extended
or abrupt run), those checks are reported **NOT APPLICABLE**, never FAIL. Consistency
checks still run.

Script 2 on `cached_raw`: **55 PASS, 0 FAIL, 0 NOT APPLICABLE** (30 reference,
3 re-derivation, 22 consistency).

| mode | checks |
|---|---|
| demo26-baseline (21) | complex spectrum vs saved 23D within 7.0×10⁻¹⁰ pm/V (limit 10⁻⁸); zeros 714.028 / 1437.479 nm; Im at zeros; nRMSE of \|χ\|, Re, \|Re\| to 10⁻⁶; peak 81.491 pm/V at 1503 nm; 301 k points; prefactor; k-weight measure; diagonal cancellation; 16 pathways |
| demo26-cutoff (10) | legacy spectrum vs saved diagnostic within 6.9×10⁻⁵ (limit 10⁻⁴; saved to 6 digits); zeros 617.343 / 1326.516 nm; Im/max\|Re\| at zeros; nRMSE \|Re\| 0.0658, \|χ\| 0.2374; integration cutoff |
| kp8 (24) | selected states; k=0 energies vs raw spectrum; \|Zh₁₂\|, \|Ze₁₂\| vs nextnano dipole output; \|O\|, \|Ze\|, \|Zh\| vs independent re-derivation; envelope exactness; orthonormality; composition file; z-origin invariance and its no-Löwdin companion; branch guard ≥ Γ; k-weight measure; diagonal cancellation; prefactor |

**Script 1.**
* The default rendered deck token-matches the historical Demo 23 production deck that
  produced `cached_raw/kp8`.
* The k-extended and abrupt variants token-match the Demo 27G and 27D decks.
* The single-band decks are byte-identical to their sources.
* All three decks pass a nextnano++ `--parse` grammar check with the Free build on this
  laptop: `<parser> --parse -d <database> --threads 1 -o <scratch> <deck>`. The Free
  build needs no licence, so this check does not exercise `-l`. The `-d … -l … --threads
  … -o …` order used by `--run` is the one the Demo 27 framework used with Professional
  on the work laptop.
* **No Professional solve was run for this package.**

**Automated tests.** `python -m pytest tests` runs 55 tests, all passing on this laptop in
about 30 s:

| tests | covers |
|---:|---|
| 14 | Equation 2 algebra, invariants and k integration |
| 17 | parsers and the 8-band state reduction, including branch arrays and the non-tautological origin test |
| 15 | deck reproduction and launcher safety: nothing launched in preflight, refusal before any write, timeout → FAIL |
| 9 | full Script 2 regression, NOT APPLICABLE semantics, and a self-containment audit of runtime imports and paths |

## 12. Results and current conclusion about Figure 2d

| | kp8 (production) | demo26-baseline | demo26-cutoff (diagnostic) |
|---|---|---|---|
| Re χ² zeros (nm) | 690.60, 1388.56 | 714.03, 1437.48 | 617.34, 1326.52 |
| Im χ² there (pm/V) | +68.38, −134.63 | +27.28, −53.00 | +34.40, −73.65 |
| \|χ²\| there / max \|χ²\| | 0.39, 0.77 | 0.34, 0.65 | 0.27, 0.58 |
| \|Re χ²\| peaks (nm) | 664, 732, 1327, 1464 | 687, 753, 1374, 1505 | 546, 752, 1093, 1505 |
| \|χ²\| local minima (nm) | 697, 924, 1405 | 720, 953, 1455 | 592, 831, 1254 |
| largest \|χ²\| | 175.9 pm/V at 1336 nm | 81.5 pm/V at 1503 nm | 126.7 pm/V at 1503 nm |
| largest \|Re χ²\| | 147.8 pm/V at 1327 nm | 71.3 pm/V at 1505 nm | 118.3 pm/V at 1505 nm |
| nRMSE vs paper: \|Re χ²\| / \|χ²\| | 0.265 / 0.322 | 0.238 / 0.262 | 0.066 / 0.237 |
| correlation vs paper: \|Re χ²\| / \|χ²\| | 0.09 / −0.09 | 0.31 / 0.25 | 0.94 / 0.44 |
| beats the best flat line with r ≥ 0.5 | no / no | no / no | yes / no |

Paper features: peaks 540, 760, 1080, 1520 nm; near-zeros 605, 1330 nm. The best flat
line scores nRMSE 0.190 against the normalized paper curve.

### What the numbers support

**The zero-crossing mechanism (all three modes).** χ² is complex. At each wavelength
where Re χ² changes sign, |χ²| = |Im χ²| is 27–77% of the largest |χ²|. The nearest local
minimum of |χ²| is still 26–76%. |χ²| only gets small in the short-wavelength tail, far
from any resonance.

So in these calculations the drops to zero between resonances appear in |Re χ²| and never
in |χ²|. Figure 2d touches zero between resonances. This **supports the interpretation**
that the published curve behaves like |Re χ²|, or like the output of a calculation whose
imaginary part was effectively absent. It cannot tell those two apart ("Re was plotted
and the axis label is wrong" versus "the calculation was effectively real-valued"). That
needs the authors' code.

**The shape comparison tells you much less.**
* In `kp8` and `demo26-baseline`, both |Re χ²| and |χ²| do worse than the best flat line
  and correlate weakly (r ≤ 0.31). Their nRMSE values say nothing about which observable
  was plotted.
* Only in the `demo26-cutoff` diagnostic does a curve beat the flat line: |Re χ²| gives
  nRMSE 0.066 at r = 0.94, while |χ²| gives 0.237 at r = 0.44. The whole
  "|Re χ²| matches better" argument from spectrum shape rests on that diagnostic.

**k-cutoff features move with k_max.**
* In `kp8`, truncating the solved range at 0.05 → 0.075 → 0.1·π/a moves the dominant
  |Re χ²| peak 1422 → 1379 → 1327 nm. The Re zeros move 720/1441 → 708/1418 → 691/1389 nm.
* In `demo26-cutoff`, the |Re χ²| nRMSE is 0.237, 0.189, 0.066 and 0.150 at k_max = 0.1,
  0.15, 0.2 and 0.25·π/a. The close match is specific to 0.2·π/a (= 0.1·2π/a).

### What is not confirmed

**The four-peak match.** The self-consistent 8-band calculation with correctly identified
heavy holes does **not** reproduce Figure 2d at the solved k range. Its |Re χ²| does
worse than a flat line (nRMSE 0.265, r = 0.09). Both sensitivity variants give the same
verdict (nRMSE 0.262 and 0.266).

The main difference is in the heavy holes. The correct e2–hh2 overlap is 0.81, where the
historical e2–"hh2" overlap (with the light-hole doublet) was 0.38, and that channel
dominates: the largest peak sits at 1327–1336 nm.

It is open whether a genuine 8-band dispersion out to 0.1·2π/a, or abrupt interfaces,
would change this. Each needs one Professional run: `--k-max-per-nm 1.11142887846
--k-points 601` and `--interface abrupt`.

## 13. Limitations

* M(k) = M(0): the deck exports spinors at k = 0 only, so matrix elements are frozen.
* Spin branches at k∥ ≠ 0 cannot be paired without finite-k spinors. Production averages
  the four pairings (splitting up to 11.7 meV); doublet-averaged energies change χ² by up
  to 12% of its maximum.
* Dispersion columns are energy-sorted, not tracked by overlap. The branch guard is
  11.84 meV here and is recorded on every run.
* Scalar envelopes are renormalized within their block. Weighting by the conduction-block
  amplitude instead changes χ² by up to 6.9%.
* Isotropic in-plane integration along one k direction.
* Four states (two electron, two heavy hole), no excitons, no light-hole pathways, no
  anti-resonant terms: Equation 2's own truncation.
* The sign of Im χ² follows Equation 2's `+iΓ` convention.
* The absolute pm/V scale depends on N_z, r_e,hh and the prefactor convention.
* The paper curve is an eye digitization of the published figure, not author data. A
  shape comparison is informative only when a curve beats the best flat line
  (nRMSE 0.190) and correlates at r ≥ 0.5.

## 14. Self-containment and developer tools

At runtime the scripts use only the Python standard library, NumPy, SciPy, Matplotlib
and files inside this folder. A test enforces this for imports and paths.

`tools/build_fixtures.py` and `tools/build_reference.py` are **developer tools**. They
were run inside the original repository to copy `cached_raw/` and `validation/decks/` and
to build `validation/reference_demo26.json`. Someone reproducing the work never needs them.

| folder | contents |
|---|---|
| `src/` | `runner.py`, `decks.py` (Script 1); `nextnano_io.py`, `kp8_states.py`, `raw_inputs.py`, `equation2.py`, `reporting.py`, `validation.py`, `analysis.py` (Script 2) |
| `config/` | `runner.json` (structure, solver and k-grid defaults), `analysis.json` (Γ, units, wavelength grid, cutoffs, thresholds) |
| `decks/` | the production kp8 deck and the two historical single-band decks |
| `cached_raw/` | shipped Professional output (provenance and SHA-256 inside) |
| `validation/` | digitized paper curve, historical reference spectra, historical decks, `reference_demo26.json` |
| `tests/` | pytest suite |

## 15. Troubleshooting

* `results root not found`: pass `--input` pointing at the folder that contains `kp8/`.
* `mode demo26-cutoff unavailable`: the historical modes need the single-band folders.
  Run Script 1 with the default `--jobs all`, or use `--mode kp8`.
* `fewer than two heavy-hole doublets`: a changed structure bound fewer states; raise
  `num_holes` in `config/runner.json`.
* NOT APPLICABLE rows are expected when you analyse a deck or config other than the
  shipped defaults. Only FAIL rows indicate a problem.
* `min_member_gap_eV` FAIL (below Γ): energy-sorted dispersion columns may have crossed a
  selected branch. Inspect `checks` in `derived_inputs.json`.
* `--run` exits with code 2 and writes nothing: read the printed reason (missing file,
  Free build, or an output folder that already holds results).
* Grammar check `SKIPPED` means no nextnano++ parser was found. The check is optional;
  pass `--parser-exe` and `--parser-database` to enable it.
