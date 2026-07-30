# Demo 2 — one-band finite quantum well

## Learning objective

Extend Demo 1 with the one-band Γ-electron Schrödinger equation. Learn the
difference between a conduction-band edge and an eigenenergy, finite-barrier
penetration, probability normalization, and physical bound-state
classification.

Enabled: Demo 1 classical bands plus one-band electron eigenstates and
probability densities. Disabled: doping, Poisson/self-consistency, strain,
polarization, multiband k·p, transport, and optics.

Physical controls are well/barrier width, Al fraction, and temperature.
Numerical controls are grid spacing, quantum-region padding, and the number of
requested states. A state is classified as bound only when its energy is below
the barrier and its integrated well probability passes the configured
threshold; its ordinal number alone is never used.

## Run

```powershell
conda activate NMIP
python .\nextnano\demos\02_one_band_finite_quantum_well\run.py
```

A licensed successful run adds eigenenergy and normalized probability CSVs,
band/probability plots, and extracted observables to the manifest. Probability
is integrated on the output grid and normalized before well, barrier, and
boundary fractions are reported. The probability plot has units of 1/nm. No
wavefunction amplitude is presented as an energy or given a misleading
vertical energy offset.

Pass requires finite ordered energies, at least one physically bound state,
primarily well-localized ground-state probability, negligible outer-boundary
probability, approximate raw-output normalization, valid band edges, a clean
log, and successful solver exit.

Common failures are wrong output globs/column indices for a solver version,
too-small quantum region, too-small barriers, too-coarse grid, or requesting
continuum-like states. Before Demo 3, understand why a wider well lowers the
ground-state confinement energy and why wavefunctions penetrate finite
barriers.

The nextnano++ 3.0.0 licensed run on 2026-07-30 established the installed
output layout used by this parser: `energy_spectrum_k00000.dat`, a combined
`probabilities_k00000.dat` table, and `bandedges.dat` columns ordered as
position, Γ, HH, LH, SO, and the two Fermi levels.
