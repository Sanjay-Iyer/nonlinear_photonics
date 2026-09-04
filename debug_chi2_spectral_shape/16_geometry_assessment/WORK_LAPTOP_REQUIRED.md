# Work-laptop calculation required for the remaining geometry/physics test

The home-laptop cache contains the correct 30.0 nm Case 04 scalar/envelope solve: 7.1 nm GaAs thick well, 1.8 nm Al0.55Ga0.45As tunnel barrier, 2.9 nm GaAs thin well, 18.2 nm period barrier, and 1.0 nm linear grading at all four interfaces. Those k=0 states are exactly the frozen Demo 21 inputs used here.

What is missing is not the scalar geometry; it is a true k-resolved 8-band solve of that same geometry. The local cache has only Gamma/HH k00000 state files and no tracked kp8 spinors or matrices versus k_parallel. A new nextnano++ Professional run on the work laptop is therefore needed to test finite-k mixing without inventing states.

Required outputs: Ee1(k), Ee2(k), Eh1(k), Eh2(k); eigenvector/spinor composition versus k; robust band/state labels or overlaps for state tracking; and, if available, k-dependent electron-hole overlaps and intra-band position/momentum matrix elements. Preserve the full 30 nm cell and the intended linear-versus-abrupt structure as separate runs.
