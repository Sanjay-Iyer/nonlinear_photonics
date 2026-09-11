# Demo 28 — nextnano to χ⁽²⁾ in two steps

This is a self-contained, clearly named copy of the current Demo26_Condensed
workflow. The calculation code and numerical inputs are preserved. No earlier
demo directory is imported or read at runtime. Copy this whole folder to your
friend's computer; they only need the two numbered scripts below.

## Step 1: generate the electronic structure

`01_run_nextnano.py` generates input decks and launches nextnano++ Professional.
nextnano calculates energies, in-plane dispersions and envelope wavefunctions.
You need your own licensed installation and material database for a solve.

From this folder, on the work laptop:

```powershell
python -m pip install -r requirements.txt
python 01_run_nextnano.py --preflight --no-parse
python 01_run_nextnano.py --run --exe "C:/path/to/nextnano++_Intel_64bit.exe" --database "C:/path/to/database.nnp" --license "C:/path/to/License_nnp.lic"
```

Executable, database and license can also be supplied through NEXTNANO_EXE,
NEXTNANO_DATABASE and NEXTNANO_LICENSE. `--output` and `--threads` are configurable.
The default without `--run` is preflight; it never launches a licensed solve.
`--no-parse` also skips optional executable-based grammar checking.

Defaults preserve the existing calculation: 1D, eight-band k·p, GaAs wells in
Al0.55Ga0.45As barriers, 300 K, [100] growth, 7.1/1.8/2.9 nm nominal
well/barrier/well widths, 1 nm graded interfaces, and a 30 nm structure.
The quantum boundary is Dirichlet; the run is quantum-only with no Poisson loop.
The in-plane path has 301 points up to 0.1*pi/a. Two auxiliary single-band jobs
provide the historical comparison inputs. With `--jobs kp8`, only the eight-band
job runs.

## Step 2: calculate and plot χ⁽²⁾

```powershell
python 02_calculate_chi2.py --input output/raw
```

Python reads the raw output, selects states, derives matrix elements, evaluates
the implemented Equation 2 with +iΓ (Γ=5 meV), integrates over in-plane momentum,
and generates real, imaginary, absolute-real and complex-magnitude results.
It preserves complex values until the observable is selected. Outputs go to
`output/analysis` unless `--output` is given.

## Run now at home, without nextnano

Real cached raw files are included:

```powershell
python 02_calculate_chi2.py --input cached_raw --check-reference
python -m pytest tests -q
```

The default analysis processes all available modes. These modes are separate
calculations, not alternative names for identical physics:

| Mode | Meaning |
|---|---|
| `kp8` | The source package's eight-band-derived envelope model, using HH-character selection and an average over spin-branch pairings. Uses frozen k=0 reduced envelopes; it is not a full finite-k multiband optical operator calculation. |
| `demo26-baseline` | Original Demo 26 mixed-input baseline: kp8 dispersion shifts with single-band energy anchors and matrix elements. |
| `demo26-cutoff` | Historical four-peak diagnostic: extrapolated parabolas, a doubled cutoff and abrupt-reference matrix elements. |

To obtain only the familiar four-peak comparison:

```powershell
python 02_calculate_chi2.py --input cached_raw --mode demo26-cutoff --check-reference
```

The cached cutoff mode uses a clearly labeled supplied matrix-element checkpoint:
its original abrupt-case raw envelopes were unavailable. A fresh Step 1 run can
generate the corresponding auxiliary raw dataset. The baseline and kp8 modes
derive their required matrices from the bundled raw envelopes.

## Files your friend receives

| File/folder | Purpose |
|---|---|
| `01_run_nextnano.py` | First user entry point: nextnano launcher. |
| `02_calculate_chi2.py` | Second user entry point: raw-data analysis and plotting. |
| `requirements.txt` | Python libraries to install. |
| `config/` | Solver and susceptibility settings. |
| `decks/` | nextnano input templates/reference decks. |
| `src/` | Internal physics, parsing, plotting and validation code. No manual editing needed to run the workflow. |
| `cached_raw/` | Original solver outputs plus explicitly documented supplied historical input. |
| `validation/` | Preserved reference spectra, paper digitization, reference checks and decks. These are comparison targets, not calculated output. |
| `tests/` | Automated checks specific to this portable package. |
| `output/analysis/` | Generated results, plots, numerical spectra and validation reports. |
| `METHODS_FROM_DEMO26.md` | Detailed inherited methodology. Historical claims/test counts are labeled as such. |

## What the results mean

The plotted quantities are Re χ², Im χ², |Re χ²| and
|χ²|=sqrt(Re²+Im²). The paper points are eye-digitized approximations.
Normalized magnitude comparisons divide each curve by its own maximum. The
combined signed Re/Im plot uses the same unnormalized pm/V axis for both parts;
neither component is independently rescaled. The absolute paper comparison uses
explicitly labeled separate axes, so compare their numerical scales as well.

The historical cutoff diagnostic reproduces the close |Re| shape comparison.
It uses extrapolation and a hard integration endpoint, so that agreement does
not establish physical resonance validity. The other modes do not reproduce
the four-peak paper curve closely. Absolute pm/V values follow the stated
prefactor/density convention; this is not an independent absolute calibration.

There is no explicit carrier-population dynamics model. An imaginary response
from the complex denominators is not by itself an absorption coefficient.
Changing solver version or material database may change fresh-run results.

## Validation

The current machine-run checks are recorded in `output/analysis/VALIDATION.md`
and `validation.json`. Historical numerical targets are preserved; they are not
regenerated to make a changed calculation pass. The new Demo 28 test results
are reported in `VALIDATION_DEMO28.md` after execution.

No licensed nextnano simulation was performed on the home laptop. Preflight,
cached-data calculations, plot generation, and regression tests can run there.
