# Demo 29 — solver-temperature dependence of selected-subband χ²

**Current status:** 29A is developing the full-8-band 300 K baseline. The
first finite-k pilot exported nine complete state frames, but only k=0 is
inside the required positive Γ→y interval. The optical operator remains
unresolved. 29B full-8-band 100/300/500 K production remains paused. 29C is
the separately labeled historical mixed-model temperature control: the matched
300 K result exists, and 100/500 K controls can now be acquired.

## Next WORK session: three separate jobs

Copy/paste commands and exact ZIP names are in [WORK_COMMANDS.md](WORK_COMMANDS.md).

After these changes are published and pulled on WORK, from the Demo 29 folder:

```powershell
python scripts\run_nextnano.py --check
python scripts\run_nextnano.py --run --temperature 300 --pilot-finite-k
python scripts\run_nextnano.py --run --temperature 100
python scripts\transfer_mixed.py --pack nextnano\work_runs\100K
python scripts\run_nextnano.py --run --temperature 500
python scripts\transfer_mixed.py --pack nextnano\work_runs\500K
```

This pilot runs **only an 8-band job**. It retains the 301-point Γ→y dispersion
through `0.10 π/a` and the existing geometry, mesh, state pool and solver
temperature. For state export it replaces `k_integration_disabled{}` with a
small `k_integration{}` grid: `relative_size = 0.03`, `num_points = 5`,
`num_subpoints = 1`, `symmetry = none`, and `force_k0_subspace = no`.
The first actual pilot had `relative_size = 0.10`, `num_points = 2`, and its
positive-y endpoint was 1.5478201 nm⁻¹. Linear scaling of that observed extent
predicts about 0.464346 nm⁻¹ at 0.03, inside the 0.555714439232 nm⁻¹ target.
The increased `num_points` is intended to provide nearby samples. This is an
empirical pilot prediction, **not** an assertion about nextnano's exact grid;
the diagnostic reads the actual `k_points.txt` and determines success from its
coordinates. See the [nextnano k-grid explanation](https://www.nextnano.com/docu/nextnanoplus/latest/tutorials/general_k_integration.html)
and [state-output definition](https://www.nextnano.com/docu/nextnanoplus/latest/reference/keywords/quantum/region/output_states.html).
`output_states{ all_k_points = yes }` requests unshifted
CB/HH/LH/SO component envelopes and composition. The licensed WORK solver must
confirm the deck and actual file layout. No licensed solve is performed on HOME.

The terminal prints a status block about every 15 seconds with start/current
time, elapsed time, job, parse/solve stage, PID, whether the process is running,
last output age, newly detected frame IDs, composition/envelope counts, and the
latest solver message. Frame counts are a **rough progress indicator**, not a
nextnano completion percentage. On exit it prints total runtime and a
finite-k coverage summary, even if the solver fails.

Each pilot gets a unique output folder under
`nextnano/work_runs/pilot_finite_k_300K_<timestamp>/` and a unique run ID.
Persistent diagnostics live in `nextnano/run_logs/300K/<run_id>/`:
`runner.log`, `run_manifest.json`, `paths_report.txt`,
`finite_k_diagnostic.json`, `finite_k_diagnostic.txt`, `output_tree.txt`, and
per-stage `stdout.log`/`stderr.log`. The debug ZIP is printed at the end as
`nextnano/run_logs/300K/<run_id>/demo29_300K_debug_<run_id>.zip`.
The original solver result is never overwritten. **Send the small debug ZIP to
the HOME LLM first.** Transfer full raw scientific data only after the pilot
proves the needed files exist.

A pilot is useful when it reports the 301-point dispersion and at least three
complete state frames on the positive Γ→y target interval, including k=0 and
two nearby nonzero points. Each frame needs composition, 14 states × eight
parseable complex component envelopes, and the dipole/momentum tables. The
diagnostic reports actual kx, ky, kz, |k|, direction and file coverage for every
integration point. A passing pilot alone does
not establish state output on every one of the 301 dispersion points, the
full-8-band optical operator, or a χ² spectrum. The integration grid and
dispersion path remain distinct nextnano calculations.

To diagnose any **existing** run without rerunning nextnano:

```powershell
python scripts\collect_debug.py --input nextnano\work_runs\300K --temperature 300
```

The standalone command writes a new timestamped debug folder and ZIP under
`nextnano/run_logs/300K/`; it reads the input folder without changing it. On
HOME, the returned original run can be inspected with:

```powershell
python scripts\collect_debug.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_300K_original_solver\300K --temperature 300
```

The ZIP contains executed decks, Demo 29 configuration, a redacted environment
and execution manifest, solver logs (capped if very large), path checks,
warning/error excerpts, a relative file tree with sizes and timestamps, a
finite-k JSON/text diagnostic, and short heads/tails of key text files. It
does **not** contain full `.dat` arrays, wavefunctions, credentials, or license
contents. If the pilot fails, send the ZIP plus the terminal's `ERROR` or
`WARNING` line and the printed run ID.

Each temperature has two matched nextnano++ jobs:

| Path | Solver input | Scientific role |
|---|---|---|
| 29A/29B full 8-band | 8-band energies and complex eight-component spinors along the target path | New primary model; 300 K pilot and optical mapping still in development |
| 29C mixed control | That temperature's 8-band dispersion **plus** that temperature's single-band anchors/envelopes | Operational historical-method trend control; acquire 100/500 K now |

The old Demo 28 raw data is never a Demo 29 production input. Its mixed 300 K
spectrum may later be plotted as an explicitly historical reference. The two
Demo 29 models need not agree numerically.

## Fixed calculation

The only planned difference between the 100, 300 and 500 K deck pairs is the
nextnano `global{ temperature = ... }` field. The 8-band Gamma-to-y path has 301
nodes through `0.555714439232 nm^-1 = 0.10 pi/a` for `a = 0.565325 nm`.
Geometry, 1 nm grades, mesh, boundaries, 6-electron/8-hole candidate-state pool,
growth-direction intersubband position, 5 meV broadening, Equation 2's 16
pathways, 400–1850 nm 1 nm wavelength grid, radial trapezoidal weights, spin and
prefactor constants start from the prior standard calculation. The first deck
requested **unshifted complex CB/HH/LH/SO spinors and composition at every k**,
but the returned Professional run emitted those fields only at k=0. The
`output_states/all_k_points` setting applies to the `k_integration{}` grid,
not to the separate `dispersion{}` path. A technical acquisition change is
required before 29A/29B can use finite-k matrices. If six/eight states prove
insufficient for tracking, a new common
configuration for all three temperatures must be reviewed before producing the
final sweep.

The planned full 8-band path uses raw 8-band energy anchors and derives finite-k
same-band `<i|z|j>` from complex spinors. The first finite-k pilot supports
that derivation at nine integration points, but only k=0 lies on the target
dispersion interval, so it cannot remove `M(k)=M(0)` there. Its selected-subband Equation 2 optical
coupling also requires the gate in [OPTICAL_MAPPING.md](OPTICAL_MAPPING.md).

## Directory map

```text
29_temperature_chi2_study/
  config/study.json, config/optical_operator.json
  chi2/                          local acquisition, parsing, tracking, Eq2, analysis
  scripts/                       runnable entry points
  nextnano/inputs/               local 300 K reference deck templates
  nextnano/prepared/             generated 100/300/500 K decks; no solver results
  nextnano/work_runs/            ignored original Professional results on WORK
  nextnano/transfer/             ignored compact transfer folders on WORK
  nextnano/raw/{100,300,500}K/  ignored returned packages on HOME
  outputs/29A_full8band_baseline/
  outputs/29B_temperature_full8band/
  outputs/29C_mixed_control/
  outputs/comparison/
  tests/                          synthetic software fixtures only
```

Python 3.10+ with `requirements.txt` is needed on both computers. On HOME the
existing `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe` has the required
scientific packages; `python` below means the active project Python. A licensed
nextnano++ Professional executable is needed **only** for the WORK `--run` command.

## HOME — preparation (already safe on this laptop)

From the repository root:

```powershell
cd nextnano/demos/29_temperature_chi2_study
python scripts/run_nextnano.py --check
python scripts/run_nextnano.py --prepare
python scripts/audit_dependencies.py
python -m pytest tests -q -p no:cacheprovider --basetemp outputs/test_local
```

`--prepare` writes both decks for every temperature under `nextnano/prepared/`.
It does not invoke nextnano or verify actual finite-k output. Inspect the decks and `deck_check.json`
before committing. Publish the Demo 29 branch, then fetch it on WORK.
Do not stage `nextnano/work_runs/`, `nextnano/transfer/`, returned `nextnano/raw/`
or any zip; they are ignored and move outside Git.

## Historical 300 K acquisition (already completed)

The runner takes `NEXTNANO_EXE`, `NEXTNANO_DATABASE` and `NEXTNANO_LICENSE`
environment variables, falling back to the existing gitignored
`nextnano/config/paths.local.yaml` (`nextnano++: exe/database/license`). It runs a
grammar parse before each licensed job. `--run` refuses an existing result folder
and wrote the exact decks, logs and run metadata under `nextnano/work_runs/300K/`.
The original full-8-band
pack attempt failed on the changed energy-file layout; the revised packer
checks frame coverage first and rejects this run because only one
spinor-composition frame exists.
The initial pack attempt may have left an ignored partial `nextnano/transfer/300K`
folder. The original solver folder is about 4 MB. Archive that **unchanged**
folder as `demo29_300K_original_solver.zip`, copy the zip HOME, and retain the
original on WORK. Do not substitute k=0 spinors for missing finite-k spinors.

A separate legacy `--pilot` switch changes the dispersion to three points and
does not exercise the 301-point finite-k question. Use `--pilot-finite-k` above
for the next WORK test. Neither pilot can be packaged or analyzed as a
production result.

## HOME — analyze the returned 300 K mixed control

The original solver folder has been copied to the HOME raw-data store at
`C:\code\nonlinear_photonics\nextnano_raw\demo29_300K_original_solver\300K`.
From this Demo 29 folder, run:

```powershell
python scripts/calculate_mixed.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_300K_original_solver\300K --output outputs/29C_mixed_control/300K
```

The mixed-control command has now succeeded on HOME. It validates the exact executed decks, matched
temperature, successful jobs, 301-point 0.10π/a dispersion, k=0 composition,
and single-band anchors/envelopes before calculating. This uses **only the new
matched 300 K pair**. The original zip should be retained unchanged; it is not
the full-8-band numeric bundle format and `transfer_raw.py --unpack` does not
apply to it. No 29A finite-k preparation is possible from this run. The actual
control output is recorded in [RESULTS.md](RESULTS.md).

Once 29A's optical mapping is scientifically established and frozen, put its
sourced parameters in `config/optical_operator.json` and implement the gated
selected-subband response step. At present that gate intentionally prevents an
unjustified primary χ² spectrum; [RESULTS.md](RESULTS.md) records the status.

## WORK — 29C mixed-model controls now

The standard `--run --temperature 100` and `500` commands each run a matched
8-band dispersion job and single-band job at the same temperature. They do not
enable experimental finite-k state acquisition. The runner displays parse and
solver status about every 15 seconds and preserves any completed run if the
next command fails. Execute each line separately from this Demo 29 folder:

```powershell
python scripts/run_nextnano.py --run --temperature 100
python scripts/transfer_mixed.py --pack nextnano/work_runs/100K
python scripts/run_nextnano.py --run --temperature 500
python scripts/transfer_mixed.py --pack nextnano/work_runs/500K
```

The two small archives are
`nextnano/transfer/demo29_100K_mixed_raw.zip` and
`nextnano/transfer/demo29_500K_mixed_raw.zip`. Each has eight scientific text
files, the two executed decks, run metadata, logs, and a SHA-256 manifest.
Copy those two ZIPs HOME through the existing transfer route. Keep the original
WORK solver folders. The 300 K reference is already on HOME and does not need
a new licensed solve.

On HOME, from this Demo 29 folder, after placing the ZIPs under
`C:\code\nonlinear_photonics\nextnano_raw\`:

```powershell
python scripts/transfer_mixed.py --unpack C:\code\nonlinear_photonics\nextnano_raw\demo29_100K_mixed_raw.zip
python scripts/transfer_mixed.py --unpack C:\code\nonlinear_photonics\nextnano_raw\demo29_500K_mixed_raw.zip
python scripts/calculate_mixed.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_100K_mixed_raw --output outputs/29C_mixed_control/100K
python scripts/calculate_mixed.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_500K_mixed_raw --output outputs/29C_mixed_control/500K
```

Once all three mixed spectra exist:

```powershell
python scripts/plot_temperature.py --model mixed
python scripts/plot_electronic_temperature.py
```

The prepared comparison plotting script also accepts `--model full8` and
`--model both` once reviewed full-8-band spectra exist for all three temperatures.
`--model historical` compares a new full-8-band 300 K spectrum against the
explicitly labeled old mixed 300 K fixture, without an agreement threshold.
It refuses incomplete inputs.

## Target full-8-band returned data contract

Once a supported finite-k acquisition is established, each compact zip will
have one top-level `<temperature>K/` folder. The full-8-band portion is:

- `full8/dispersion.npz`: 301 k vectors/energies and direction;
- `full8/frames/k00000.npz` through `k00300.npz`: all 14 state IDs, energies,
  CB/HH/LH/SO fractions, spatial grid and **eight complex128 spinor components**;
- `native_metadata/`: solver `simulation_info.txt` and any emitted small
  dipole/momentum matrix tables for interpretation checks.

The control portion `mixed/` has the raw dispersion and k-vector tables,
8-band k=0 energy and composition, and single-band Gamma/HH k=0 energies and
envelopes. These are the eight raw files the local historical control consumes.
Both exact executed decks, logs, run metadata, source-file hashes and package
hashes are included. Parsed numbers round-trip exactly into the compact frames;
the original text remains on WORK. This is intentionally larger than the former
eight-file-only proposal because finite-k state tracking and optical contractions
must remain revisable at HOME.

## Interpretation

This measures how **nextnano solver temperature changes electronic structure and
the resulting selected-subband χ²**, subject to the approved optical mapping.
Equation 2 has no explicit Fermi–Dirac or dynamic carrier-population factor; this
does not represent every finite-temperature effect. 500 K is a deliberately high
sensitivity point, not an asserted normal operating temperature.
