# Reproduce Demo 26: paper, real chi2, imaginary chi2

## Short explanation to send with this folder

We used nextnano++ to calculate the electronic structure of a GaAs/AlGaAs
asymmetric coupled quantum well. Python then evaluated the implemented
Equation-2 susceptibility expression from the energy differences and
wavefunction-derived matrix elements, including the complex broadening terms.
Demo 26 compares the resulting real part, imaginary part and magnitude with
approximate points read from the paper's Figure 2d.

The recent four-peak comparison is a separate parabolic-cutoff diagnostic,
not the original nextnano-dispersion baseline. This folder reproduces both
so they cannot accidentally be mistaken for the same calculation.

## Run the recent comparison (default)

Unzip the complete folder, open a terminal in it, and use Python 3.10 or newer:

```text
python -m venv .venv
```

Activate that environment (`.venv\Scripts\activate` on Windows cmd, or
`source .venv/bin/activate` on macOS/Linux), then:

```text
python -m pip install -r requirements.txt
python reproduce.py
```

No nextnano installation, license, repository, or original machine paths are
needed for this offline numerical reproduction. NumPy and Matplotlib are the
only external dependencies. Tested versions are recorded in verification.json.

The script recomputes chi2 from inputs.json; the reference CSV is used only to
check the result. It creates results/diagnostic/ containing:

- paper_magnitudes.png: paper + |Re chi2| + |chi2|.
- paper_re_im.png: paper + signed Re chi2 + signed Im chi2.
- spectrum.csv: calculated components and normalized signed components.
- verification.json: comparison error, normalization and approximate roots.

For the ORIGINAL Demo 26 input spectrum, run:

```text
python reproduce.py --mode baseline
```

This writes results/baseline/. These baseline plots intentionally use the same
clean three-curve layout for comparison; they are not pixel copies of all the
original Demo 26 report figures. The script verifies the full complex spectrum
against the saved 23D spectrum with an absolute tolerance of 1e-8 in its historical
pm/V convention. The diagnostic reference was saved with only six significant
digits, so its comparison tolerance is 1e-4 in unscaled response units.

## What was run in nextnano

The actual production input is included as data/nextnano_production.in. Its
contents, rather than its introductory comment, specify a LINEARLY GRADED
structure. It is a nextnano++ one-dimensional, eight-band k.p quantum calculation:

| Setting | Value in the copied production deck |
|---|---|
| Material | GaAs wells, Al0.55Ga0.45As barriers, GaAs substrate |
| Temperature | 300 K |
| Growth direction | [100], simulation coordinate x |
| Total structure | 30 nm |
| Nominal sequence | 9.1 barrier / 7.1 well / 1.8 barrier / 2.9 well / 9.1 barrier, nm |
| Interfaces | 1 nm linear composition grading at all four interfaces |
| Mesh | 0.05 nm spacing specified at active interfaces; 0.5 nm at outer ends |
| Quantum domain | x = 7.1 to 22.9 nm; Dirichlet boundaries |
| States requested | 6 electron and 8 hole states; output count 14 |
| Momentum path | Gamma toward y=[010], 301 points, 0 to 0.555714439232 nm^-1 |
| Momentum endpoint | 0.1*pi/a, a=0.565325 nm |
| Density setting | no_density = yes |
| Run block | quantum only; no self-consistent Poisson loop in this deck |
| Bias | 0 V Fermi contact |

The deck requests energies, envelopes, probabilities, spinor compositions and
matrix elements. Requesting all-k output does not establish that the solver
actually exported all-k spinors: the prior analysis found only k=0 spinors in
the available output. No populations evolving under illumination were computed.

To rerun the electronic structure, open the included .in file with a licensed
nextnano++ installation and run it using your own material database and license.
No executable or license is distributed. Matching the input alone does not
guarantee bitwise agreement across nextnano versions/material databases; the exact
solver version and database checksum have not been established in this bundle.

The resulting nextnano files do not directly contain this chi2 spectrum. The
Python processing steps below are also required. For exact numerical comparison,
use the supplied frozen inputs first, then compare newly generated inputs with
them. This package does not include a general parser/state tracker for arbitrary
new nextnano output.

### The kp8 deck is one of three nextnano calculations

Demo 26 combines inputs from three separate nextnano++ runs. All three decks are
included:

| Quantity | Deck in data/ | nextnano model | Interfaces | Used by |
|---|---|---|---|---|
| In-plane dispersion E(k) | nextnano_production.in | 8-band k.p, dispersion path | 1 nm linear grading | baseline (tracked samples), diagnostic (parabola curvatures A) |
| k=0 energies | nextnano_single_band_case04_linear_1nm.in | single-band Gamma{} + HH{}, 6 states each | 1 nm linear grading | both modes |
| Matrix elements O, ze, zh | nextnano_single_band_case04_linear_1nm.in | single-band Gamma{} + HH{} | 1 nm linear grading | baseline |
| Matrix elements O, ze, zh | nextnano_single_band_case00_abrupt.in | single-band Gamma{} + HH{} | abrupt | diagnostic |

The two single-band decks are identical except that Case 04 adds four
ternary_linear grading regions (x = 8.6-9.6, 15.7-16.7, 17.5-18.5 and 20.4-21.4 nm).
Both use the same grid, quantum domain x = 7.1-22.9 nm, Dirichlet boundaries,
300 K and no_density = yes. They are the Demo 20 rendered decks, which are identical
to the Demo 19 decks that produced the stored table apart from the comment header.

O and z are not nextnano outputs. Python integrated the normalized single-band
envelopes from output_states: O_nm = integral of psi_e,n psi_hh,m dz, and
z = integral of psi z psi dz. The decks also request overlap_integrals{}, but that
output was not used.

So in the diagnostic mode the energies and dispersion describe the GRADED structure
while the matrix elements describe the ABRUPT one.

## Original baseline processing

1. The earlier analysis selected two electron branches and two valence branches
   from the kp8 output (historical labels e1/e2/hh1/hh2). The observed k=0 Kramers
   pairs were 11+12, 13+14, 5+6 and 3+4, respectively; these are dataset-specific,
   not universal nextnano state numbers. Pair energies were averaged.
2. The saved tracked table includes raw energies and separately aligned energies.
   Each aligned branch is the raw kp8 branch plus ONE constant shift that makes k=0
   equal the single-band Case 04 energy: e1 -11.35 meV, e2 -30.13 meV,
   hh1 +4.03 meV, hh2 -3.96 meV, identical at every k. So the kp8 run supplies only
   the shape of E(k); the k=0 energies are single-band values. The portable script
   uses the exact aligned samples that reproduce the preserved 23D spectrum.
3. Matrix elements were frozen at k=0, M(k)=M(0), from Demo 19 Case 04 (1 nm
   linear grading), a separate single-band nextnano run rather than the kp8 run
   (see the table above). We supply those values directly. Overlap O is
   dimensionless; ze and zh are position matrix elements in nm. No wavefunction
   reconstruction from energies is performed by this script.
4. The historical Demo 22 chi2_from_k_inputs engine summed eight electron-side
   and eight valence-side pathways, with opposite signs. Denominators are
   (DeltaE-2*Ephoton+i*Gamma)(DeltaE-Ephoton+i*Gamma), with Gamma=0.005 eV.
5. Radial trapezoid weights are g_s*k*dk/(2*pi), g_s=2. Integration stops at
   0.1*pi/a. The wavelength grid is 400 through 1850 nm in 1 nm steps.
6. Its prefactor uses Nz=1/(30 nm), r_e,hh=0.751 nm, e and epsilon0, with the
   nm/eV conversion implemented explicitly. The output is reported in the
   historical pm/V convention. This normalization is a reproduction choice,
   not a resolved validation of the paper's absolute scale.
7. The spectrum was saved as demo_results/demo24/demo23_reanalysis/spectra/
   23D_chi2.csv. Demo 26's run_demo26_real.py reads its real, imaginary and
   magnitude columns. A later Demo 26 verification script also calls the
   Demo 22 engine directly.

The portable baseline function preserves the historical algebra for these REAL
matrix inputs. Do not assume it is a correct general complex-spinor implementation:
an earlier audit found missing conjugations for arbitrary complex input matrices.
State identity also remains a limitation: a prior audit found the branch labeled
hh2 to be predominantly light-hole-like. The source Case 04 table carries
physical_valid=False. Matching a saved spectrum is numerical reproduction,
not proof of physical validity.

## Recent cutoff diagnostic: the plots discussed with your friend

This mode reproduces outputs/CUTOFF_ARTIFACT_FINDING/fig2d_chi2_diagnostic.py.
It uses parabolas E(k)=E0+A*k^2 rather than the original tracked kp8 dispersion.
The energy anchors match graded Case 04, while the frozen matrices are from
Case 00, the abrupt reference. This is a mixed-input diagnostic. All exact
constants are included in inputs.json under diagnostic.

It integrates analytically to K=0.1*(2*pi/a), with a=0.56533 nm, twice the
baseline cutoff. The measure is 2*pi*k*dk. It also uses the historical diagnostic's
opposite overall pathway sign. Its default -i*Gamma matches the recent separate
Re/Im figure. The older cutoff calculation used +i*Gamma: conjugation changes
the sign of Im but leaves Re, |Re| and |chi| unchanged for these real inputs.
This package preserves those plotting conventions without claiming a universal
sign of absorption independent of Fourier convention.

IMPORTANT UNIT CORRECTION: cutoff_test.py returns the unscaled integral sum; it
does not apply the absolute susceptibility prefactor. Earlier notes labeled its
raw peak of about 41.18 as pm/V. That label is not justified by that function.
The diagnostic CSV here therefore has generic real/imag columns and the plots
are dimensionless. No physical factor-of-96 absolute-scale conclusion should
be inferred from this unscaled number.

The diagnostic gives Re zero crossings near 617.3 and 1326.5 nm. Im remains
nonzero there. The paper points have near-zero values at 605 and 1330 nm:
alignment is approximate, not exact. This supports a real-part-based shape
interpretation for this model but does not identify the authors' full pipeline.
The shorter-wavelength peak pair is sensitive to the arbitrary hard cutoff;
recovering those peaks does not validate them as material resonances.

## Plot normalization and physical interpretation

Paper points are eye-digitized approximations to the published simulated curve,
not the authors' numerical dataset. Divide them by their maximum (3950).
In the signed-component plot, divide BOTH Re and Im by max|Re|. In the separate
magnitude comparison, divide |Re| and |chi| by their respective maxima, matching
the earlier comparison. No vertical guide lines are used.

Re and Im come from the same complex calculation. |chi|=sqrt(Re^2+Im^2).
The plots do not calculate a nonlinear absorption coefficient or time-dependent
carrier density. The implementation has no explicit occupation probabilities;
any implicit population assumptions in the paper's derivation still need checking.

## Provenance

provenance.json identifies repository source paths and SHA-256 hashes of inputs.
inputs.json is the compact portable numerical input. The copied production deck
and configuration document the original nextnano setup; the configuration is
for reference, not required by reproduce.py. The original data and analyses are
not changed by the portable script.
