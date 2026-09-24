# Demo 29 — solver-temperature dependence of selected-subband χ²

**Status after the first WORK acquisition:** the new 300 K 8-band and 300 K
single-band Professional jobs completed, but the 8-band output contains only
`k00000` spinors/composition. The separate dispersion path has 301 k points.
The full-8-band baseline and temperature sweep are **paused**; no production
susceptibility has been claimed. Preserve the original 300 K work-run folder.

Each temperature has two matched nextnano++ jobs:

| Path | Solver input | Scientific role |
|---|---|---|
| 29A/29B full 8-band | 8-band energies and complex eight-component spinors at all 301 k points | Planned primary model; the current solver deck did not export finite-k spinors, and optical mapping remains gated |
| 29C mixed control | That temperature's 8-band dispersion **plus** that temperature's single-band anchors/envelopes | Historical-method trend control |

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
same-band `<i|z|j>` from complex spinors. The current run cannot support that
derivation or remove `M(k)=M(0)`. Its selected-subband Equation 2 optical
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
existing `C:\Users\iyer95\miniconda3\envs\ai\python.exe` has the required
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

## WORK — first acquisition: 300 K only

From the repository root, after activating the existing project Python environment:

```powershell
git fetch origin codex/demo29-temperature-chi2
git switch --track origin/codex/demo29-temperature-chi2
cd nextnano/demos/29_temperature_chi2_study
python scripts/run_nextnano.py --check
python scripts/run_nextnano.py --run --temperature 300
Compress-Archive -LiteralPath 'nextnano\work_runs\300K' -DestinationPath 'demo29_300K_original_solver.zip'
```

The runner takes `NEXTNANO_EXE`, `NEXTNANO_DATABASE` and `NEXTNANO_LICENSE`
environment variables, falling back to the existing gitignored
`nextnano/config/paths.local.yaml` (`nextnano++: exe/database/license`). It runs a
grammar parse before each licensed job. `--run` refuses an existing result folder
and writes the exact decks, logs and run metadata under `nextnano/work_runs/300K/`.
The first two commands already completed on WORK. The original full-8-band
pack attempt failed on the changed energy-file layout; the revised packer
checks frame coverage first and rejects this run because only one
spinor-composition frame exists.
The initial pack attempt may have left an ignored partial `nextnano/transfer/300K`
folder. The original solver folder is about 4 MB. Archive that **unchanged**
folder as `demo29_300K_original_solver.zip`, copy the zip HOME, and retain the
original on WORK. Do not substitute k=0 spinors for missing finite-k spinors.

A short output-coverage pilot is available before the full run if the WORK solver
version's all-k output behavior is uncertain:

```powershell
python scripts/run_nextnano.py --run --temperature 300 --pilot
```

This separate three-point 8-band pilot cannot be packaged or analyzed as a
production result. The full 301-point run is still required.

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

## WORK — remaining temperatures after the 300 K review

**Paused. Do not run 100 K or 500 K with the current 8-band deck.** The
following commands describe the intended order only after an amended,
pilot-verified acquisition emits the required finite-k states on the fixed
301-point Γ→y grid for all temperatures:

```powershell
python scripts/run_nextnano.py --run --temperature 100
python scripts/transfer_raw.py --pack nextnano/work_runs/100K
python scripts/run_nextnano.py --run --temperature 500
python scripts/transfer_raw.py --pack nextnano/work_runs/500K
```

Copy `demo29_100K_raw.zip` and `demo29_500K_raw.zip` HOME. For each zip, run the
same `transfer_raw.py --unpack`, `prepare_full8.py` and `calculate_mixed.py`
commands with its temperature in the paths. Add
`--reference-bundle nextnano/raw/300K` to each 100/500 K `prepare_full8.py`
invocation so k=0 doublet labels are compared by spinor-subspace overlap to
the new 300 K run. Use `outputs/29B_temperature_full8band/100K_prepared` and
`outputs/29B_temperature_full8band/500K_prepared` as those preparation outputs.
Review any inconsistent matches. Once all three mixed spectra exist:

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
