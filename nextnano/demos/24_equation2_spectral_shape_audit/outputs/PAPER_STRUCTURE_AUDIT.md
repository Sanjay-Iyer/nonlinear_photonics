# Paper/model structure audit

The comparison is not demonstrably apples-to-apples because the published Fig. 2d simulation appears to be the ideal design while Demo 23 uses 1-nm linear interfaces.

| Parameter | Paper | Demo 23 | Match? | Confidence | Potential spectral consequence |
|---|---|---|---|---|---|
| thick/thin GaAs wells | 7.1 / 2.9 nm (10 nm total, s=0.42) | 7.1 / 2.9 nm | YES | high | none |
| tunnel barrier | 1.8 nm Al0.55Ga0.45As | 1.8 nm Al0.55Ga0.45As | YES | high | none |
| period barrier / period | 18.2 nm / 30 nm by Fig. 1 and layer arithmetic; page 6 says 20 nm inconsistently | 18.2 nm / 30 nm | LIKELY | high | Nz scale only for isolated periods |
| interfaces | Fig. 2d design simulation appears ideal/abrupt; EDS-profile simulations are treated separately | linear 1 nm at all four interfaces | NO / UNCERTAIN | medium | changes energies, overlaps and z matrix elements; can alter normalized shape |
| temperature | not stated for Fig. 2d calculation | 300 K | UNKNOWN | low | band gap and resonance shifts |
| tensor element | chi_xzx^(2) | Equation-2 chi_xzx^(2) | YES | high | none |
| state count | first two conduction and first two HH states only | two plus two in Equation 2 | YES | high | extra-state hypothesis is low priority |
| broadening | 5 meV | 5 meV | YES | high | none |
| wavelength/observable | fundamental wavelength, simulated \|chi^(2)\| | fundamental wavelength, complex chi and \|chi\| | YES | high | Re-only zeros cannot be compared as full paper nodes |
| k cutoff | saturation asserted at 0.1 BZ | 0.1 pi/a | FORMALLY | medium | copied result is numerically not converged versus 0.125 pi/a |
