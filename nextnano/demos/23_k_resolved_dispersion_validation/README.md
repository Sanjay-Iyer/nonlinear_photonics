# Demo 23 — k-resolved dispersion validation for Equation 2

Demo 23 asks how much the validated Equation 2 susceptibility changes when
only the four in-plane subband dispersions are improved. It is not a new
Equation 2 implementation.

All four modes share the Demo 21 Case 04 geometry, the same Professional
nextnano++ 8-band input family, state tracking, radial grid, wavelength grid,
broadening, normalization, prefactor, and validated k=0 matrix elements.

| Mode | Dispersion model |
|---|---|
| 23A | Demo 20/21 shared reduced-mass parabolic transition shift |
| 23B | Separate anchored parabolas for e1, e2, hh1, and hh2 |
| 23C | Boss model: electron parabolas plus interpolated nonparabolic hh1/hh2 |
| 23D | Interpolated tracked kp8 energies for all four states |

Every mode keeps `M(k) = M(0)`. Full finite-k matrix elements are explicitly
outside Demo 23.

## Physics kept fixed

- Equation 2's eight conduction-side and eight heavy-hole-side pathways.
- The electron-minus-heavy-hole cancellation.
- `Gamma = 5 meV`, used in the energy-domain complex denominators.
- `r_e,hh = 0.751 nm`.
- `Nz = 1/(30 nm)`, interpreted as one asymmetric coupled-QW period per 30 nm.
- Spin degeneracy `g_s = 2`.
- Production k measure `g_s k dk/(2 pi)`, corresponding to
  `d^2k/(2 pi)^2` per unit area.
- `k_BZ = pi/a`, `a = 0.565325 nm`, and nominal `kmax = 0.1 pi/a`.

The bare `2 pi k dk` convention and the two-individual-wells interpretation of
`Nz` are diagnostics only. They are never silently substituted into the A-D
comparison.

The residual `1/hbar` shown in the boss derivation requires clarification
before implementation. Demo 23 retains the validated energy-domain conversion,
in which the two denominator conversions cancel the original `hbar^-2`.

The default quantitative acceptance gate for the boss hybrid is a 23C-vs-23D
relative spectral RMSE of at most 1%, together with passing k-grid, kmax, state
tracking, and isotropy gates. The threshold is explicit in `demo23_config.yaml`.

## Commands

Run from the repository root in the work-laptop Python environment:

```powershell
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --preflight --machine .\nextnano\config\machines\nextnano_machine.work.yaml
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --tests
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --generate-inputs
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --physics --machine .\nextnano\config\machines\nextnano_machine.work.yaml
```

Analyze an already completed run without rerunning nextnano:

```powershell
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --analyze .\demo_results\demo23\demo23_YYYYMMDDTHHMMSSZ
```

Regenerate tables, reports, and plots from existing solver output:

```powershell
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --plots-only .\demo_results\demo23\demo23_YYYYMMDDTHHMMSSZ
```

Run/report a single model. The 23A regression gate still executes first:

```powershell
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --physics --mode 23A --machine .\nextnano\config\machines\nextnano_machine.work.yaml
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --physics --mode 23B --machine .\nextnano\config\machines\nextnano_machine.work.yaml
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --physics --mode 23C --machine .\nextnano\config\machines\nextnano_machine.work.yaml
python .\nextnano\demos\23_k_resolved_dispersion_validation\run_demo23.py --physics --mode 23D --machine .\nextnano\config\machines\nextnano_machine.work.yaml
```

Because the kp8 data are shared, the normal efficient workflow is one unfiltered
`--physics` run followed by mode-filtered `--analyze` commands.

## Fail-loud behavior

`--physics` exits nonzero if the Professional executable, database, or license
is unavailable; a solver call fails; explicit k vectors are absent; spinor
composition is missing; target-state tracking is ambiguous; interpolation
would extrapolate; or the 23A regression gate fails. No synthetic physics
spectrum is generated in any of those cases.

## Professional combined-dispersion output

The observed Professional build writes the complete path to
`QuantumDispersions/.../dispersion_<path>.dat` with explicit vectors in
`kVectors_<path>.dat`; `Quantum/.../energy_spectrum_k00000.dat` and the spinor
composition contain only k=0. Demo 23 reads that layout directly, including a
known formatting defect where the Band 6/7 and Band 13/14 numeric fields touch.

At k=0, the frozen Demo 21 transition ladder and Cb character identify the
Kramers pairs as e1=`11+12`, e2=`13+14`, hh1=`5+6`, and hh2=`3+4` for the
observed run. Each scalar subband energy is the pair average, consistent with
the retained `g_s=2` model. Pair splittings are recorded in
`tables/state_tracking.csv`.

Because this output contains no finite-k spinors, overlap-based tracking cannot
be certified. The analysis still produces the energy-only A–D diagnostics but
marks the state-tracking gate `FAIL`/limited and does not declare the complete
boss-hybrid validation passed. This limitation is not hidden or replaced with
synthetic spinors.

## Output

Real runs are written under `demo_results/demo23/demo23_<UTC stamp>/` and
contain copied input decks, solver logs, raw Professional output, tables,
spectra, 16 internal diagnostic figure families, six paper-comparison figure
families, the resolved configuration, and `DEMO23_FINAL_REPORT.md`.

The paper comparison uses the repository's existing 45-point eye digitization
of the simulated curve in Ramesh et al. Fig. 2d. It is always labeled
`Digitized from Ramesh et al. Fig. 2d`, is not treated as raw/tabulated author
data, and is not an acceptance gate. The measured paper resonance appears only
as a separately categorized location marker; measured SH intensity is not
placed on a susceptibility axis. See `PAPER_DATA_PROVENANCE.md` and
`PLOTTING_REPORTING_AUDIT.md`.
