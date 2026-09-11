# 28M — finite-k optical-input preparation

`chi2/finite8band.py` saves component-overlap tensors and full-spinor z matrices
from the new eight-component envelopes. `eq2_inputs` requires a reviewed optical
operator and branch/spin convention before constructing the two-by-two Eq2 inputs.
No single-band anchor, frozen k=0 matrix or historical spectrum is a production
input. Existing Eq2 and k integration are reused, not rewritten.

This is not yet a certified full 8-band optical response. The scalar Eq2 mapping
and degeneracy treatment remain explicit review items; no default overlap is
silently substituted. See `../../WORK_LAPTOP_8BAND_RUN.md`.
