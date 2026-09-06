# BZ convention audit

The repository defines `k_BZ=pi/a`, hence production `kmax=0.1 pi/a = 0.5557 nm^-1`. The paper says the response saturates at “one-tenth of the Brillouin zone away from the zone center” without supplying the code's exact reciprocal-space convention. For zincblende along a conventional [010] Gamma-X line, Gamma-X is 2pi/a, so 0.1 Gamma-X would be 0.2pi/a—twice the production cutoff. “0.1 reciprocal-lattice vector” is likewise 0.2pi/a.

Existing copied data support direct calculations through 0.1pi/a and a separate 0.125pi/a sensitivity case only. The cumulative tests through 0.1pi/a are valid; 0.2pi/a is **REQUIRES_PROFESSIONAL_DATA** and was not extrapolated. Because Demo24 found appreciable change at 0.125pi/a, the cutoff convention is a **POSSIBLE ISSUE**, not a proven cause.
