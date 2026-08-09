# Demo 16G — supplied `.nnp`, 20-structure sweep, and paper benchmark

Three clearly separated groups, one optical calculation, no fitting.

| group | what | how the deck arrives |
|---|---|---|
| 1 `supplied_nnp` | the two supplied `.nnp` files | staged verbatim, SHA256 both ends |
| 2 `structure_sweep` | 20 Latin-hypercube ACQW structures | rendered by `deck16g` |
| 3 `paper_benchmark` | the paper's ideal-abrupt ACQW | rendered by `deck16g` |

From the solver call onwards every group takes the **same** path — same
invocation helper, same output discovery, same Demo 11 parse, same Demo 16F χ⁽²⁾
evaluator, same strict bound gate. That is the only way the comparison measures
structures rather than pipelines.

> **Nothing has been run.** This demo was written on a machine with no licence
> and deliberately not executed, not tested and not validated. Nothing below is
> a claim that it works — the work-laptop commands are the first real test.

## Two things reading the `.nnp` files changed

**1. The grading definition is not the one Demo 16E used.** For
`$GRADE_WIDTH = 0.7` the supplied files emit

```
ternary_linear{ alloy_x = [0.55, 0.0]  x = [$QW1_min - 0.7, $QW1_min] }
```

so 0.7 nm is the **full** 0→0.55 ramp, placed **entirely outside** the well —
the GaAs well keeps its stated width. Demo 16E's "0.70 nm grade" is a **10–90%**
width whose full ramp is **0.875 nm** and is **centred** on the interface, so
half of it eats into the well. Same number, two different structures, and not
even the same well width.

16G adopts the `.nnp` convention so Group 2 is comparable with Group 1, and
every case reports all three numbers plus the placement:

```
requested_grade_definition   full_linear_ramp_outside_well
full_linear_ramp_width_nm    0.70
10_90_width_nm               0.56          (= 0.8 x full, exact for a linear ramp)
grade_placement              outside_well
```

`grading16g.describe()` is the **only** place any of these is computed. Never
compare a 16G grading column with a 16E one without converting.

**2. The hole model differs.** Both supplied files solve holes with
`kp_6band{ num_ev = 10 }`; Demos 16E/16F use a one-band heavy-hole model. That
is a physics difference, not a formatting one. It is recorded on every Group 1
row as `hole_model`, and `nnp16g.inspect` emits a warning so no χ⁽²⁾ comparison
silently spans two hole models. Groups 2 and 3 default to `single_band_hh`;
set `quantum.hole_model: kp_6band` in the config to make them match Group 1.

## Why Group 2 does not use Demo 16E's renderer

Because of the grading definition above. Building the sweep with
`grading14.build_structure_profile` would have produced structures that are not
comparable with Group 1 — different ramp widths *and* different well widths for
the same input. So `deck16g.render` writes the supplied deck with different
numbers: same region ordering, same `ternary_linear{}` grammar, same grid
strategy, same output requests.

`ternary_linear{}` is used for every generated case. It can be, because the
grades sit outside the wells, so two of them can only meet if the barrier is
thinner than the sum of its two grades — and that case is **refused** with a
named error rather than rendered into a deck whose later region silently
overwrites the earlier one.

## The sweep

20 structures, seed `16072026`, maximin selection over 64 seeded Latin-hypercube
designs. Deterministic: same config, same twenty structures. Widths are quantised
to 0.01 nm so a structure can be rebuilt from the printed table alone. Ranges are
in `config16g.yaml`:

```yaml
thick_well:     [6.0, 8.0]
thin_well:      [2.0, 4.0]
tunnel_barrier: [0.5, 2.5]
left_grade:     [0.0, 1.4]
right_grade:    [0.0, 1.4]
```

A sampled grade ≤ `abrupt_threshold_nm` renders as a genuinely abrupt interface —
no ramp region at all, rather than a sub-mesh ramp the grid cannot carry.

## The paper benchmark

7.1 / 1.8 / 2.9 nm, s = 0.42, 18.2 nm period barrier, 30 nm period, abrupt.
Transcription is **checked**, not trusted: `cases16g.paper_benchmark_case` raises
if the total well, the asymmetry or the period do not agree with the config.

Primary target, stated in words by the paper:

```
ideal abrupt chi2 at 1550 nm = 2340 pm/V
```

Also recorded: EDS Al profile 1200 pm/V, EDS Ga profile 1363 pm/V, measured
effective ≈1400 pm/V. Fig. 2d's ~3000–4000 pm/V peak may be plotted as a
digitized **visual reference** and is labelled as digitized — it is never a
target, and a digitized curve is never presented as raw paper data.

## No empirical scaling, enforced

`config16g.yaml` carries `optics.absolute_scale_factor: null`, and
`cases16g.load_config` **raises** if it is ever set. Every χ⁽²⁾ comes from the
physical calculation. Demo 16F's two unresolved published ambiguities — the
factor of 3 between Eq. 1 and Eq. 2 as printed, and the unstated heavy-hole m_j
multiplicity — are reported on every result with `applied: false` and are never
multiplied in.

Optical conventions are 16F's promotable set, and `optics16g.conventions_from`
refuses anything else: `N_z = well_density`, zone edge
`gamma_to_x_2pi_over_a`, disc domain, and **both** k implementations (radial and
independent Cartesian) run on every case so their agreement is a standing check.

## Output layout

```text
<results_root>/16G_paper_nnp_and_structure_sweep_comparison/demo16g_<stamp>_<uid>/
  cases/<group>/<case_id>/
    logs/     case.log, solver_stdout.log, solver_stderr.log, command.txt
    input/    the staged .nnp copy, or the generated .in deck
    raw/      nextnano++ output
    parsed/   envelopes.csv, quasi_bound_states.json, chi2_spectrum.csv, chi2_spectra.json
    plots/
    provenance.json, resolved_config.yaml
  summaries/
    demo16g_master_summary.csv     one row per case, every column below
    demo16g_master_summary.json    the same, plus conventions and paper comparison
    sweep_design.json              seed, ranges, maximin diagnostics
    grading_convention.json
  plots/
    supplied_nnp_wavelength_response.png       Plot 1
    structure_sweep_wavelength_response.png    Plot 2
    paper_benchmark_wavelength_response.png    Plot 3
    chi2_wavelength_all_groups.png             Plot 4
    chi2_at_1550_comparison.png
    peak_wavelength_comparison.png
    peak_chi2_comparison.png
    detuning_from_1550_comparison.png
    energy_transitions_comparison.png
```

The master CSV carries, per case: group, case_id, source, representation,
hole_model; thick/thin/barrier/total well, asymmetry, period barrier; all three
grading numbers and the placement for both interfaces; E1, E2, HH1, HH2,
E2−E1, HH1−HH2, E1−HH1, E2−HH2; all four e–hh overlaps; all six ⟨ψ|z|ψ⟩ plus
both diagonal differences and the centroid separation; localization
probabilities; χ⁽²⁾(1550), peak χ⁽²⁾, peak wavelength, detuning, tensor, and the
Cartesian/radial agreement; pass/fail with stage and reason, bound-state verdict,
`physical_qc_valid`; and provenance — solver executable, return code, input path
and hash, raw and parsed directories, machine config, `scale_factor_applied`.

## Debugging

`--verbose` prints, for every case: case id, group, source and generated input
paths, solver executable, database, licence, machine config, results directory,
structure dimensions, grading representation and definition, full ramp
coordinates, mesh spacing, quantum model, requested states, the solver command,
return code, log locations, expected vs discovered output files, parsed energies,
bound-state QC, optical status, χ⁽²⁾(1550) and the spectral peak — and a full
traceback for anything that fails.

A failing case is recorded and the run continues
(`execution.continue_on_case_failure`). Exceptions are written down, never
swallowed.

## Highest-risk integration point

`runners16g.effective_padding_nm`. Demo 11's analysis derives its localization
region edges from `domain_padding_nm`, and 16G places grades *outside* the wells,
so the thick well starts one full left ramp further in than Demo 14 assumes. The
runner passes an effective padding so `active_start` lands on `well1_start`.
**If localization numbers look shifted on the work laptop, check this first.**

## Commands

See the bottom of this file's companion message, or run `--plan` — it prints
every resolved path, both file hashes, all twenty structures with both grading
widths, and the paper targets, without launching a solver.
