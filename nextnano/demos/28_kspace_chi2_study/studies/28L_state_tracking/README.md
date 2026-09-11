# 28L — finite-k candidate state tracking

`chi2/finite8band.py` consumes validated returned data, checks full spinors and
tracks candidate states by maximum adjacent-k overlap, flagging ambiguous or
degenerate assignments. It does not assume fixed columns are physical HH states.
Degenerate-subspace resolution and final branch selection require later review.
No returned dataset has been processed yet.
