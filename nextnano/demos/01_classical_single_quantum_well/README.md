# Demo 1 — classical GaAs/AlGaAs single quantum well

## Learning objective

Learn how nextnano++ represents a 1D grid, two material regions, alloy
composition, interfaces, temperature, and classical band edges.

The physical stack is AlGaAs / GaAs / AlGaAs. GaAs has the lower Γ conduction
edge and therefore forms the electron well. The interfaces are at the left
barrier width and at that coordinate plus the well width.

## Physics boundary

Enabled: material properties and classical Γ, heavy-hole, light-hole, and
split-off band edges. Disabled: Schrödinger equation, Poisson,
self-consistency, intentional strain calculation, polarization, transport, and
optics. A mandatory neutral zero-bias contact is present for nextnano++ input
validation; it does not enable those disabled calculations.

Edit physical widths, aluminum fraction, and temperature under `scientific` in
`demo.yaml`. Grid spacings under `numerical` control discretization, not the
physical device.

## Run

```powershell
conda activate NMIP
python .\nextnano\demos\01_classical_single_quantum_well\run.py
```

Expected run-directory files include the generated input, resolved YAML,
machine summary, console log, and manifest. A licensed successful run also
creates raw nextnano outputs, `extracted/band_edges.csv`, and
`plots/band_edges.png`.

Pass requires solver exit success, a completion marker, no fatal marker, finite
values, a strictly increasing position axis, sampled interfaces, and a higher
AlGaAs Γ conduction edge than in GaAs. If the band-edge file layout differs
for the installed version, inspect it and update only the explicit column map
in `demo.yaml`.

Before advancing, answer: Which layer is the electron well? Where are the two
interfaces? Why does more aluminum raise the barrier? Why does changing well
width move interfaces but not create quantum levels? Which YAML values are
physical and which are numerical?

Licensed validation completed on 2026-07-30 with nextnano++ 3.0.0
(2026-06-16 kernel): the deck was accepted, wrote Γ/HH/LH/SO band edges, and
finished with `DONE.` without enabling a quantum or Poisson block.
