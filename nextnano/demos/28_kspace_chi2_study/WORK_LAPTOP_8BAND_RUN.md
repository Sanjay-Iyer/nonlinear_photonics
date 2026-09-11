# 28K / 28L / 28M — acquisition handoff

Status: preparation only. No new Professional data or new physics results exist.
28A–28J and Equation 2 are retained unchanged. This is separate from the earlier
28C work-laptop plan; use the command below for the new extended 8-band run.

## One run

From the repository root on the WORK laptop, with the project Python environment active:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --run
```

Paths come from the same gitignored `nextnano/config/paths.local.yaml` the other
demos use (`exe`, `database`, `license` under `nextnano++:`), so nothing extra is
needed if that file is already filled in. `NEXTNANO_EXE`, `NEXTNANO_DATABASE`,
`NEXTNANO_LICENSE`, or `--exe`/`--database`/`--license` override it (flag > env > yaml).
Do not put license contents in Git. Install the package's `requirements.txt` in the
Python environment if needed. No new Python dependency is introduced.

During `--run` a progress line prints every 60 s (`--progress-interval N` to change):

```
[1h12m00s] ~ 18.4% | ETA 5h19m40s | k 221/1201 | per-k files 42,871/232,994 | raw files 43,020 | <last solver.log line>
```

nextnano++ prints no per-k counter, so the percent is a rough estimate: per-k output files
on disk (energy spectrum + composition + 24×8 envelopes per k) over the 232,994 expected.
The ETA extrapolates the file-writing rate. If the percent stays near 0 while `raw files`
and the log keep moving, nextnano++ is holding per-k output until the end (or writing only
k=0); let it finish and let the validator decide. The same snapshot is in `<result>/progress.json`; the full solver
output is in `<result>/solver.log` (`Get-Content <result>\solver.log -Tail 20 -Wait`).
Ctrl+C kills the solver and records the interruption; rename/delete that result before re-running.

The runner checks syntax first, refuses a Free executable and refuses an existing
result directory. `--preflight` checks syntax without a physics solve;
`--dry-run` has the same safe behavior. `--no-parse` is a static-only check and is
not a grammar PASS. `--run` always requires its own successful grammar check.

## Settings and outputs

Edit `config/extended_8band.json`; preflight materializes the exact deck and a
snapshot `outputs/28K_extended_8band/work_laptop/runner.json`. The source config,
not that generated snapshot, is authoritative.

| Setting | Requested value |
|---|---|
| Solver | nextnano++ Professional, 8-band k·p, LAPACK |
| Grid | 1201 points on one Gamma-to-y radial path |
| Endpoint | 0.20 pi/a = approximately 1.11142887846 nm^-1 |
| Lattice constant | 0.565325 nm |
| Spacing | approximately 0.000926190732 nm^-1 |
| States | 8 electron + 16 valence solver states (24 total, spin resolved) |
| Structure | Same 300 K asymmetric GaAs/AlGaAs wells and spatial grid as Demo28 |
| Quantum region | 7.1–22.9 nm, Dirichlet boundaries, no density solve |
| Resource controls | 4 threads, 24-hour timeout; configurable |

The 24 states provide candidate branches for tracking; they do not assert that
all candidates are bound or that all must enter the existing 16-pathway Eq2.
Requested outputs include energies, k vectors, all eight complex envelope
components, CB/HH/LH/SO composition and partial probabilities at every k,
growth-direction dipoles, growth/in-plane momentum matrices, and material data.
This may produce about **230,592 individual envelope files** plus other raw files.
Leave substantial disk space and transfer the complete directory, preferably as
an archive preserving its internal paths. Runtime and size are not benchmarked here.

`analysis_cutoffs_pi_over_a` sets the future sweep; `presentation_cutoffs_pi_over_a`
sets the five clean overlays. Intermediate cutoffs reuse native samples and
recompute endpoint weights; no new nextnano calculation is needed.

## What preflight establishes—and does not

Static checks and the installed nextnano++ Free grammar parser accept the deck.
Only `--parse` was executed on the home laptop. The installed nextnano++ 3.0.0
manual, PDF pages 1219 and 1233, describes `all_k_points` output for k-integration
or dispersion points. Pages 170–172 and 1133 distinguish finite-k solving from
k=0-subspace approximations and multidirectional integration grids.
We use an explicit radial dispersion path, **not** `k_integration num_points=1201`,
which is a per-direction sampling parameter and can expand quadratically in 1D structures.

Grammar acceptance is not proof that a particular Professional build will emit
all requested files. The runner checks actual grid, direction, state count,
per-k energies/composition, full envelope filename coverage, exact deck/config,
and transfer hashes after execution. A k=0-only archive fails; no fallback is used.
If a version uses a different file naming/index scheme, retain the whole raw run
and inspect its k/energy correspondence before adapting the reader.
The return validator checks presence; 28L additionally parses and checks envelope
normalization, orthogonality and agreement with composition.

## Future 28L / 28M analysis

After transfer validation, from the Demo28 directory:

```powershell
python scripts/prepare_returned_8band.py --input nextnano/extended_8band_work_results
```

This writes only new `outputs/28L_state_tracking/returned_data/` products:
candidate branch/solver IDs, energies and band characters, adjacent-k overlap
scores, ambiguity flags, and per-k component-overlap tensors and z matrices.
It retains complex phases. It never reads old single-band anchors or freezes
matrices at k=0. Existing output destinations are refused.

**Optical mapping review is still required before calling the new response
“fully 8-band χ².”** A full-spinor inner product between distinct eigenstates is
not the paper's interband envelope overlap. `chi2/finite8band.py::eq2_inputs`
requires an explicit dimensionless Bloch optical operator in the documented
eight-component basis, its source, branch selection, spin convention and model
scope. It contracts the saved component tensor with that operator and uses
finite-k full-spinor z matrices and raw energies. Degeneracy/assignment flags
require an explicit resolution; individual doublet labels are not automatically
physical branches. Full degenerate-subspace tracking/reduction is not implemented.

This adapter preserves the existing two-electron/two-valence Eq2 model; it does
not implement an unrestricted 24-state nonlinear-response theory. No default
optical operator is invented. The external unit-cell length `r_e_hh`, broadening,
spin factor, period and radial/isotropic integration assumptions must be recorded
and reviewed for the selected model; they are not all measured by nextnano.
Default historical values are not automatically proof of a consistent mixed-band
optical prefactor. Equation 2 itself remains in `chi2/equation2.py` unchanged.

`chi2/extended8band_plots.py` supplies future signed Re/Im overlays, 1550-nm cutoff
curves, isolated-peak diagnostics only in a reviewed window, selected candidate
energy/HH–LH plots, and same-cutoff historical-reference comparisons. It saves
the exact χ² inputs, per-cutoff spectra, integration weights and metadata.
No production spectrum or plot was generated in this preparation task.

## Git and transfer

Commit the Demo28 code/config/docs/tests and generated 28K preflight deck/metadata.
The rest of Demo28 must also be committed if it is still untracked; these helpers
import local Demo28 modules, not previous demos. Review the scoped Git diff/status;
do not use a repository-wide `git add -A` because unrelated changes exist.
The new raw result directory is ignored by Git. Pull the same commit on WORK,
run once, and follow `TRANSFER_BACK.md`. No code was committed or pushed for you.
