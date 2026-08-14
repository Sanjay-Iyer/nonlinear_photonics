# Demo 17E — statistical interface roughness and grading sweep

**Production follow-up to Demo 17 and Demo 17D.** One fixed paper-geometry
GaAs/Al₀.₅₅Ga₀.₄₅As asymmetric coupled quantum well, solved **21 times** with the
licensed `nextnano++` binary: the ideal abrupt reference plus **20 seed-locked
random interface-grading realizations**. Interface grading is the only thing that
varies.

```bash
python nextnano/demos/17e_statistical_grading_sweep/run_demo17e.py --preflight
```

```bash
python nextnano/demos/17e_statistical_grading_sweep/run_demo17e.py --physics --verbose
```

`--physics` requires the **work laptop's licensed installation**. The home
laptop's Free nextnano++ 3.0.0 build caps at 100 grid points and this deck needs
several thousand, so `--structure` and `--physics` both stop there — but
`--preflight` and `--syntax` run everywhere and do parse every deck against the
real grammar.

---

## The question

Demo 17 solved ten structures that differ in barrier thickness, well asymmetry,
grading width *and* deck representation at once. That is the right design for a
structure survey and the wrong one for a slope: no column of its table isolates
grading. Demo 17E nails everything else down —

| held fixed | value |
|---|---|
| asymmetry `s` | 0.42 (7.10 nm / 2.90 nm wells, 10.0 nm total) |
| central barrier | 1.80 nm |
| aluminium fraction | 0.55 |
| grading family | linear |
| deck representation | native `ternary_linear` (abrupt for `case_00`) |
| mesh | 0.05 nm |
| broadening Γ | 5.0 meV |

— and varies only the 10–90 % interface transition widths. A difference between
two rows of the study summary is a difference in interface roughness and cannot
be anything else.

## What is inherited, and from where

Demo 17E adds no new physics and no new correction. Everything load-bearing is
imported and reused rather than reimplemented:

| piece | source |
|---|---|
| geometry and composition builder | Demo 14 (`demo14`, `grading14`) |
| deck rendering, realized-composition gate, metrology | Demo 16E (`demo16e`) |
| gated licensed solve | Demo 16B (`demo16b`) |
| Eq. 2 absolute χ⁽²⁾ evaluator | Demo 11 (`demo11`) |
| corrections A, B, C and the bound-state verdict | Demo 17 (`demo17`) |
| **deck template** | Demo 17's `graded_acqw17.in.j2`, **by reference** |

The template is not copied. `demo17e.yaml` points at
`../17_paper_chi2_reproduction_corrected/graded_acqw17.in.j2`, and preflight
asserts the resolved path is the file Demo 17 itself solves with, so the two
demos cannot drift apart.

### The three corrections, carried over verbatim

| | correction | value here |
|---|---|---|
| **A** | N_z counts individual wells | 2 / 30 nm = 6.666667 × 10⁷ m⁻¹ |
| **B** | zincblende 2π/a zone edge | k_max = 0.10 × 2π/a = 1.111429 nm⁻¹ |
| **C** | Dirichlet box moved clear | 35.0 nm cladding, 30.0 nm quantum padding |

Correction C gives an **81.80 nm domain** with a **71.80 nm quantum box** around
an 11.80 nm active region. They are re-verified on every config load by
`demo17.verify_nz_convention`, `verify_k_space_convention` and
`verify_domain_convention` — the same functions Demo 17 uses, not copies.

---

## Case generation

`case_00` is the ideal abrupt reference and is **Demo 17's `case_02`, field for
field**; `cases17e.assert_matches_demo17_reference` makes that an error rather
than a footnote. It is also the one case the paper quotes an absolute number for
(2340 pm/V for ideal abrupt interfaces).

`case_01` … `case_20` are drawn **hierarchically**, because that is what a growth
run is:

```
sigma_run ~ TruncNormal(mu = 0.70 nm, sd = 0.30 nm) on [0.20, 1.40] nm
sigma_i   =  sigma_run + delta_i,   delta_i ~ Normal(0, 0.08 nm)
```

for three interfaces sampled independently:

| key | interface | position |
|---|---|---|
| `gaas_to_algaas_barrier` | GaAs → AlGaAs tunnelling barrier | z2 |
| `algaas_to_gaas_well` | AlGaAs → GaAs well | z1 and z3 |
| `gaas_to_algaas_cladding` | GaAs → AlGaAs period cladding | z4 |

**Why hierarchical rather than flat i.i.d.** Two reasons, and both matter. The
interfaces of one wafer share a substrate temperature, a V/III ratio and a growth
rate, so their widths are strongly correlated and the large variation is run to
run — which is what STEM/EDS across wafers actually shows. And averaging three
independent draws shrinks the ensemble's spread by √3: a flat model produced
twenty realizations that all looked the same and a severity grouping with one
member in each tail (18/1/1). The hierarchy keeps the per-interface independence
and puts the spread where the physics puts it.

**Determinism.** Every draw is one uniform from a `random.Random(17005)` Mersenne
Twister stream mapped through an exact inverse CDF (`statistics.NormalDist`).
Both are stdlib and both are documented as reproducible across Python versions,
so a realization depends on the seed and on nothing else — not the numpy version,
not the platform, not what ran before it. Truncation is done in probability space
rather than by clipping, so no mass piles onto the bounds. `--write-cases`
freezes the 21 definitions into `validation_cases.yaml`, and **preflight
regenerates the list from the seed and compares it record for record** on every
run, so "seed-locked" is tested rather than asserted.

### The rise tie — read this before quoting a per-interface width

`grading14.build_structure_profile` takes **one width per growth direction**, not
one per interface, because one growth process makes every interface it makes. The
two GaAs → AlGaAs interfaces (z2, z4) share a chemistry, so Demo 17E:

* **samples them independently** — both values are drawn, frozen and reported;
* **renders their mean**, and records `rise_tie_residual_nm` per case.

Across the frozen 20 the tie moves each rise interface by **0.044 nm on average
and 0.151 nm at worst**. Forking the composition builder to grade all four
interfaces independently would fork the path Demo 16E's realized-composition gate
and Demo 17's entire comparison rest on, which is a much larger claim than a
roughness sweep needs to make. If per-interface rendering is ever wanted, that is
a change to `grading14` with its own validation demo, not a flag here.

### The frozen ensemble (seed 17005)

| | mean σ (nm) | min | max | sd |
|---|---:|---:|---:|---:|
| mean interface width | 0.805 | 0.291 | 1.141 | 0.253 |
| run-level width | 0.821 | 0.267 | 1.193 | 0.266 |
| GaAs→AlGaAs barrier | 0.821 | 0.433 | 1.239 | 0.249 |
| AlGaAs→GaAs well | 0.792 | 0.200 | 1.156 | 0.267 |
| GaAs→AlGaAs cladding | 0.816 | 0.300 | 1.263 | 0.264 |

Severity split **sharp 3 / moderate 10 / severe 7**. The sample mean of 0.805 nm
sits about 1.6 standard errors above the declared μ = 0.70 nm; that is what this
draw is, it is recorded rather than corrected, and no seed was searched for.

| case | severity | mean σ | barrier | well | cladding |
|---|---|---:|---:|---:|---:|
| case_00 | *reference* | 0.0000 | abrupt | abrupt | abrupt |
| case_01 | severe | 1.1245 | 1.1506 | 1.1277 | 1.0920 |
| case_02 | sharp | 0.2907 | 0.4630 | 0.2000 | 0.2997 |
| case_03 | moderate | 0.6022 | 0.5477 | 0.6539 | 0.5535 |
| case_04 | moderate | 0.7969 | 0.9082 | 0.7162 | 0.8470 |
| case_05 | moderate | 0.8836 | 0.8578 | 0.9030 | 0.8705 |
| case_06 | severe | 1.1248 | 1.0658 | 1.0851 | 1.2632 |
| case_07 | severe | 1.1242 | 1.0011 | 1.1564 | 1.1827 |
| case_08 | severe | 0.9060 | 0.9522 | 0.8549 | 0.9621 |
| case_09 | sharp | 0.3543 | 0.4329 | 0.3225 | 0.3393 |
| case_10 | moderate | 0.7948 | 0.7467 | 0.8623 | 0.7080 |
| case_11 | severe | 1.1406 | 1.2385 | 1.1040 | 1.1158 |
| case_12 | moderate | 0.8686 | 0.8448 | 0.8839 | 0.8617 |
| case_13 | moderate | 0.6291 | 0.6162 | 0.5988 | 0.7026 |
| case_14 | moderate | 0.7373 | 0.6063 | 0.7989 | 0.7450 |
| case_15 | moderate | 0.7241 | 0.6407 | 0.7518 | 0.7519 |
| case_16 | moderate | 0.7982 | 0.8811 | 0.7591 | 0.7937 |
| case_17 | sharp | 0.3968 | 0.4520 | 0.3323 | 0.4707 |
| case_18 | severe | 0.9843 | 1.0869 | 0.8739 | 1.1026 |
| case_19 | moderate | 0.8421 | 0.8027 | 0.8655 | 0.8349 |
| case_20 | severe | 0.9757 | 1.1191 | 0.9834 | 0.8170 |

Two structural properties hold across the whole ensemble and are enforced, not
hoped for:

* **the mesh resolves every grade.** The narrowest ramp drawn (`case_02`, 0.20 nm
  10–90) spans 0.25 nm = **5 mesh cells** at 0.05 nm. Below 4 cells the run
  aborts: a sub-resolution grade is a bug, not a result.
* **no realization overlaps.** The widest ramp pair (`case_11`) spans 1.426 nm
  inside the 1.80 nm barrier, 0.374 nm of headroom. An overlapping barrier would
  switch production's renderer to an imported table, so one case would be
  rendered differently from the other nineteen and neither comparison would be
  clean. All 20 stay native `ternary_linear`.

---

## The dual reporting scale

Every optical quantity is written **twice**.

**Raw (1.00×)** — the defensible baseline. Demo 17's corrected Eq. 2 with no
multiplier and no fitted constant. This is the only scale in the demo that
follows from cited physics end to end, and it is the one every statistic, trend,
ratio and gate uses.

**Calibrated** — the raw value times **one declared multiplier** carried from
Demo 17D, so the pm/V figures sit on the same axis as the paper's.

| id | label | multiplier | factors (N_z × perm × tensor × dipole) | status |
|---|---|---:|---|---|
| `raw` | Raw Baseline | 1.00× | — | established |
| `combo_09` | Combined Standard | **16.80×** | 3.0 × 2.0 × 2.8 × 1.0 | *speculative* |
| `combo_10` | Full Reconciliation Budget | **27.72×** | 3.0 × 3.0 × 2.8 × 1.1 | *contradicted* |

`combo_09` is the default; `--calibration combo_10` (or `raw`) switches it, and
`--calibration X --analyze-existing RUN_DIR` re-reports a completed study at no
licensed cost. Each declared total is checked against the product of its own
factors at load time and refused if it does not close.

> **Read this before quoting a calibrated number.** These multipliers are
> **declared, not derived** — and Demo 17D did not derive them either. That sweep
> resolves the *product* of four hypothesised factors and can never attribute it;
> two of its ten combinations reach the same total by different routes; and
> combo 10 was *constructed* from Demo 17's known 27.63× residual, so its landing
> on 2340 pm/V is arithmetic rather than evidence. Combo 09 rests on a 2.8×
> tensor factor Demo 17b classed speculative. The calibrated column **aligns the
> axes; it does not validate the scale.**

That warning is stamped into `reporting_scales.yaml`, the spectral CSV header and
every `matrix_elements.json`, and preflight asserts that no gate reads a
calibrated value. A multiplier moves an amplitude and cannot move a peak
position or a ratio, which is exactly why the trend statistics live on the raw
column: reporting them there keeps them free of a declared factor they do not
depend on.

---

## Artifacts

```
<results_root>/17e_statistical_grading_sweep/demo17e_<stamp>_<sha>_<uid>/
├── RUN_STATUS.json            written before the first solve, updated after
├── README_RUN.md              the sampling plan and per-case table for this run
├── corrections_applied.yaml   corrections A/B/C, stamped before anything solves
├── reporting_scales.yaml      raw + calibrated provenance and the warning
├── validation_cases.yaml      the frozen 21, copied into the run
├── physics_summary.json       every per-case record, passed or failed
├── summaries/
│   ├── study_summary.csv          the 21-row master table
│   ├── study_summary.json         the same, plus roughness statistics and trends
│   ├── structure_summary.csv      requested vs realized composition per interface
│   └── chi2_spectrum_all_cases.csv  1400–1800 nm at 1 nm, raw AND calibrated
├── plots/                     four diagnostic figures at 300 DPI
├── cases/<case_id>/
│   ├── physics/optical/parsed/envelopes.csv          signed Eq. 2 amplitudes
│   ├── physics/optical/parsed/matrix_elements.json   the three 2×2 matrices
│   ├── physics/optical/parsed/chi2_focused.csv       this case's spectrum
│   ├── physics/wavefunctions.csv                     probability densities
│   └── plots/{composition,wavefunctions}.png
└── p00 … p20/                 raw nextnano++ output, short paths on purpose
```

`study_summary.csv` carries, per case: case name and severity, all three sampled
grading widths and the two rendered ones, E₁/E₂/HH₁/HH₂ and both transitions,
χ⁽²⁾ at 1550 nm **raw and calibrated**, peak χ⁽²⁾ **raw and calibrated**, peak
wavelength and detuning, ratios against the abrupt reference, per-state
localization, and the bound-state QC verdict.

`matrix_elements.json` is Demo 11's production artifact, **merged** rather than
replaced: the three raw 2×2 matrices stay exactly as the solver's analysis
produced them, and the named scalars, state energies and reporting scale are
added beside them.

### Figures (300 DPI)

| file | question it answers |
|---|---|
| `composition_all_cases.png` | how differently is aluminium distributed across the 21 profiles? Full active region on top, tunnelling barrier magnified below — where the realizations actually differ. |
| `chi2_wavelength_all_cases.png` | what does roughness do to the whole spectrum? All 21 curves, no normalisation, abrupt reference black and dashed on top, calibrated scale on a secondary axis. |
| `chi2_wavelength_grouped.png` | does the *spread* grow with roughness, or only the mean? One panel per severity band with a pointwise ±1σ band, sharing one y axis so the amplitude loss is visible at a glance. |
| `chi2_vs_grading_width.png` | how much χ⁽²⁾ does a nanometre of roughness cost? Peak and 1550 nm against mean σ, each with a least-squares slope and r², abrupt reference as a horizontal line. |

Demo 16E's `energy_levels_all_cases`, `wavefunction_localization_all_cases` and
`peak_wavelength_and_detuning` are drawn too, reused rather than reimplemented.

The shared `plots.save_figure` helper is fixed at 180 DPI and is shared with every
other demo, so raising it there would silently re-render the whole repository.
Demo 17E saves through its own writer at `plotting.dpi` while still recording
skips in the shared ledger, so a broken matplotlib degrades to a recorded skip
rather than destroying a multi-hour licensed run.

---

## Flags

| flag | what it does | needs a licence? |
|---|---|---|
| `--preflight` *(default)* | 27 offline checks, plus 2 more where an executable resolves | no |
| `--physics` | the full 21-case licensed solve, analysis and all plots | **yes** |
| `--verbose` | solver commands, per-case failure detail, full check output | — |
| `--write-cases` | freeze the 21 definitions into `validation_cases.yaml` | no |
| `--syntax` | render and `--parse` every deck | executable only |
| `--structure` | build every composition and gate it against the solver's own | executable only |
| `--validate` | both of the above | executable only |
| `--scales` | print the corrections, reporting scales and sampling plan | no |
| `--analyze-existing RUN_DIR` | rebuild every table and figure from a completed run | no |
| `--calibration {raw,combo_09,combo_10}` | which multiplier the calibrated column uses | — |
| `--cases ID[,ID...]` | solve only these; the full study is several hours | — |

### The preflight

27 offline checks. Six exist only in this demo and are what make the statistical
claim auditable rather than asserted:

1. the frozen list is **regenerated from the seed** and compared record for record;
2. the 0.05 nm mesh is shown to resolve the narrowest ramp, per case, in cells;
3. no realization overlaps, so all twenty render identically;
4. every case differs from the reference in grading and in **nothing else**;
5. the deck template is shown to be Demo 17's own file, not a copy;
6. both declared multipliers equal the product of their own stated factors.

Corrections A and B are checked against values computed *in the preflight* from
first principles — 2 wells / 30 nm, and 0.10 × 2π/a — rather than against
constants read out of the config, because a check that reads its expectation from
the thing it is checking cannot fail. The zone-edge guard is itself tested by
feeding it a reverted config and requiring it to raise.

---

## What this demo does not do

* **It runs no optimizer.** The 20 realizations were drawn from a declared
  distribution and frozen before the first deck was written. Nothing reads a
  result in order to choose a parameter, and a case with larger χ⁽²⁾ is described
  as such and nothing follows from it.
* **It does not re-run Demo 17's A/B ablation.** Demo 17 measured those once;
  re-measuring one convention against itself on 21 realizations of the same
  convention adds nothing. What *is* checked per case is that the conventions
  reached the evaluator — `demo17e.verify_production_settings` reads back the
  settings object each case was actually evaluated with.
* **It does not close the absolute-scale gap.** That gap is Demo 17D's subject
  and remains open. Demo 17E reports the raw residual against 2340 pm/V and
  applies nothing to it.
* **It does not vary Γ, the well widths, the barrier or the profile family.** A
  demo that varied roughness and anything else together could not attribute
  either.
