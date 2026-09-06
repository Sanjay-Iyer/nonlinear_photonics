# Concise independent professor response

The primary conclusion should be re-ranked. The leading hypothesis is the Brillouin-zone cutoff convention, not HH/LH assignment. Demo 23 uses (0.1\pi/a=0.5557\ \mathrm{nm^{-1}}), whereas zincblende GaAs has \(\Gamma X=2\pi/a\); the paper's 0.1-BZ cutoff is therefore naturally (0.2\pi/a=1.1114\ \mathrm{nm^{-1}}). The (0.125\pi/a) case already produces a paired 659/1318-nm feature. Fitting Demo 23B's \(\Delta E_{22}\) puts the paper's exact 540/1080-nm one-/two-photon pair at (k=1.1348\ \mathrm{nm^{-1}}=0.1021\,\Gamma X). The existing cutoff sweep never reaches that range.

The selected `hh2` pair is also invalid for a two-HH paper model: pair 3+4 is 97.6% LH at (k=0), while pair 1+2 is 100% HH. The attempted correction does not clear this problem because it changes only the dispersion shape while retaining the old single-band anchors and (M(0)) matrices; its worse RMSE is therefore inconclusive.

The paper plots \(|\chi^{(2)}|\), not signed \(\chi\). Demo 23D has no Re or Im crossing in either minimum window. It shows strong but incomplete electron/HH cancellation: ratios 0.0428 at 605 nm and 0.0486 at 1330 nm. The dominant cancelling pairs are `C_m1_n1_l1`/`V_m1_n1_l1` and `C_m2_n2_l2`/`V_m2_n2_l2`.

Broadening, (N_k), global normalization, and extra optical states are low priority. The alternate direction changes the current complex spectrum by only 1.99% RMSE, so anisotropy is not presently a leading cause. The literal real-envelope Equation-2 sign and indices appear correct, but any finite-(k) complex implementation must restore the conjugates implied by the bra-ket ordering.

**Top five:** (1) wrong BZ cutoff convention/domain, (2) HH2/LH state-identity and denominator/numerator mismatch, (3) abrupt-paper versus 1-nm-graded geometry, (4) frozen non-self-consistent (M(k)=M(0)), (5) possible angular anisotropy over the extended domain.

**New Professional run: YES, targeted.** First run the same graded structure along [010] to (0.2\pi/a\) with 601 points, exporting finite-(k) state character and complex matrix information. Then repeat the identical grid for the ideal abrupt paper geometry to isolate the interface effect. Validate the `all_k_points` output syntax on a tiny pilot first, because the Demo 23 deck requested it but produced only (k=0) state/matrix files.

**Confidence:** high (0.96) in the cutoff diagnosis; moderately high (0.85) in the overall ranking.
