# Paper observable audit

## What the paper explicitly says

The source is Ramesh et al., *Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells*, `C:\code\nonlinear_photonics\2602.23246v1.pdf`. On PDF page 7, Figure 2d labels the dashed simulation axis **`Simulated |chi^(2)| (pm/V)`**. The caption calls it the simulation for the coupled quantum wells. The Methods on pages 11-12 define a complex chi through denominators containing `+ i Gamma`, with Gamma = 5 meV.

## What the plot visually shows

- The simulated curve is entirely nonnegative.
- The left y axis starts at zero; it is not centered on a signed zero axis.
- The two dips near 605 and 1330 nm touch the zero baseline but no negative branch is drawn.
- The repository digitization has 45 nonnegative points and exact zero-valued samples at 605 and 1330 nm.

## What is inferred

The literal label, axis geometry, and rendered curve all support a magnitude observable, not signed Re[chi]. The colleague's interpretation can be made compatible only by assuming both that the absolute-value bars are erroneous and that negative lobes were folded upward or clipped. The paper and repository contain no affirmative evidence for either assumption. There is therefore **no evidence of a labeling inconsistency** in Figure 2d.

The signed-real comparison remains a useful falsification test, but it must not replace the paper's explicit magnitude observable. Because the eye digitization contains no sign information, it cannot independently reconstruct a signed paper curve.

Provenance limitation: `C:\code\nonlinear_photonics\nextnano\demos\23_k_resolved_dispersion_validation\paper_figure2d_digitized_simulation.csv` is an unchanged eye digitization of the published dashed curve, not raw author data.
