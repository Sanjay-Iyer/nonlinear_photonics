# Paper structure reproduction audit

| Item | Paper ideal Fig.2d | Experimental / EDS model | Demo 23 | Match |
|---|---|---|---|---|
| wells | 7.1 / 2.9 nm GaAs | nominally same | 7.1 / 2.9 nm | YES |
| central barrier | 1.8 nm Al0.55Ga0.45As | measured interface profiles | 1.8 nm Al0.55Ga0.45As | YES nominally |
| outer barrier/period | 18.2 nm / 30 nm by layer arithmetic | grown superlattice | 18.2 nm / 30 nm | LIKELY |
| interfaces | ideal/abrupt design simulation | non-abrupt EDS profiles | 1-nm linear at all interfaces | NO / NOT SAME AS IDEAL |
| temperature | not stated for Fig.2d | experiment-specific | 300 K | UNCERTAIN |
| strain/substrate/growth | GaAs/AlGaAs, GaAs substrate | experimental wafer | GaAs substrate, [100] growth | LIKELY |
| electrostatics | paper Methods says Schrödinger-Poisson | experimental carrier conditions not numerically specified | no documented self-consistency in Demo23 input audit | UNCERTAIN/NO |

Grading changes confinement energies, wavefunction centroids, overlaps, and z-matrix cancellation, so it can move resonances and reshape minima. Direction and size require a like-for-like calculation; no geometry was changed here.
