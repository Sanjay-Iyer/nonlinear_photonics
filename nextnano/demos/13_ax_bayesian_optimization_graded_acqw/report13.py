"""Demo 13's written record: the guides, the overview, and the final comparison.

Section 15 forbids explanation inside a figure, and Section 17 asks for that
explanation somewhere.  This module is that somewhere.  Every guide is
*generated* from the same catalogues the plots and tables are generated from
(:data:`plots13.PLOT_SET`, :data:`tables13.TABLE_CATALOGUE`), so a figure or a
table cannot exist without an entry describing it, and a guide cannot describe a
figure that was never drawn.

Running this file regenerates the repository's copies of the guides::

    python report13.py

The same functions write a copy into every result bundle, so a bundle that
leaves the work laptop carries its own documentation.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import yaml

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import write_text_atomically  # noqa: E402

import design13  # noqa: E402
import plots13  # noqa: E402
import synthetic13  # noqa: E402
import tables13  # noqa: E402

GUIDE_FILES: tuple[str, ...] = (
    "RESULTS_OVERVIEW.md",
    "PLOTS_GUIDE.md",
    "TABLES_GUIDE.md",
    "AX_OPTIMIZATION_GUIDE.md",
    "PAPER_COMPARISON_GUIDE.md",
    "WORK_LAPTOP_RUN_GUIDE.md",
)

_OBSERVED = "Observed — evaluated nextnano trials, drawn as markers, never smoothed."
_SURROGATE = (
    "Surrogate-predicted — a continuous mesh from the fitted Ax model, with the "
    "evaluated points overlaid as open circles so the two cannot be confused."
)

#: Per-figure guide entries. Keyed by filename so a missing entry is a test
#: failure rather than an undocumented plot.
PLOT_GUIDE: Mapping[str, Mapping[str, str]] = {
    "bo_objective_value_by_trial.png": {
        "question": "Did later trials actually score better than earlier ones?",
        "x": "Trial number",
        "y": "Objective value (a.u.)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "The initial Sobol trials scatter widely; if Bayesian optimization is working, the later trials cluster in the upper part of the range. Individual dips after the switch to the model are normal — the acquisition function deliberately spends some trials exploring.",
        "limits": "This is every completed trial including invalid ones; a high point here is not necessarily a usable design. Cross-check against the validity map and the QC table.",
    },
    "bo_best_objective_so_far_by_iteration.png": {
        "question": "How fast did the search improve, and has it stopped improving?",
        "x": "BO iteration",
        "y": "Best objective value (a.u.)",
        "encoding": "Step line; only valid trials may raise it.",
        "data": _OBSERVED,
        "read": "A monotone staircase. A long flat tail is the usual signal that further iterations are buying little, though it can also mean the model is stuck in a local region.",
        "limits": "Invalid trials never raise this curve, so it can sit below the maximum in the raw objective plot. That difference is the point, not an error.",
    },
    "bo_chi2_at_1550_by_trial.png": {
        "question": "How strong is the response exactly at the telecom target?",
        "x": "Trial number",
        "y": "|χ²| at 1550 nm (a.u.)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "In Mode A this is the objective itself. In Modes B and C it is a reported metric and may not improve monotonically.",
        "limits": "Relative units. A value at a fixed wavelength is not the structure's intrinsic strength — compare with the peak plot before concluding anything about the material response.",
    },
    "bo_peak_chi2_by_trial.png": {
        "question": "How strong is each structure at its own resonance?",
        "x": "Trial number",
        "y": "Peak |χ²| (a.u.)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "Read together with the resonance-wavelength plot: a large peak far from 1550 nm is a strong structure that is simply mistuned.",
        "limits": "The peak is taken over the configured focused window only; a resonance outside that window is invisible here.",
    },
    "bo_resonance_wavelength_by_trial.png": {
        "question": "Where does each design put its resonance?",
        "x": "Trial number",
        "y": "Peak wavelength (nm)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "Clustering toward 1550 nm over the run means the optimizer is tuning the resonance rather than only raising the amplitude.",
        "limits": "Discrete jumps can be a genuine change of which transition dominates, or a state-labelling change. Check the tracking-confidence plot at the same trial numbers.",
    },
    "bo_detuning_from_1550_by_trial.png": {
        "question": "How far off target is each design?",
        "x": "Trial number",
        "y": "Detuning from 1550 nm (nm)",
        "encoding": "Signed; the dashed line is zero detuning.",
        "data": _OBSERVED,
        "read": "The sign matters: a systematic offset means the geometry is pushing the transition energy consistently one way.",
        "limits": "The Ax constraint uses the absolute value, so points symmetric about zero are treated identically by the optimizer.",
    },
    "bo_asymmetry_vs_grading_thickness_objective.png": {
        "question": "Which part of the asymmetry–grading plane did the search visit, and what did it find?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the objective; marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "Dense colour-rich clusters are where the optimizer concentrated. Empty regions were judged unpromising by the model, not proven bad.",
        "limits": "A projection of a four-dimensional space: two points that look adjacent here can differ in barrier thickness or profile.",
    },
    "bo_barrier_thickness_vs_grading_thickness_objective.png": {
        "question": "How do tunnelling and interface smoothing trade off?",
        "x": "Central barrier thickness (nm)",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the objective; marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "Thin barriers hybridize the wells strongly; thick grades soften the same interfaces. This plane shows whether the two effects reinforce or cancel.",
        "limits": "Projection, as above. Also note that the geometric guard rejects grades wider than the narrowest adjacent layer, so the top-left corner is unreachable by construction.",
    },
    "bo_asymmetry_vs_barrier_thickness_objective.png": {
        "question": "Where is the response strongest in the two purely geometric parameters?",
        "x": "Quantum-well asymmetry, s",
        "y": "Central barrier thickness (nm)",
        "encoding": "Colour is the objective; marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "This is the plane closest to Demo 12's Stage 5 grid, so it is the fairest visual comparison against the grid search.",
        "limits": "Projection. Abrupt and heavily graded designs are superimposed here.",
    },
    "bo_grading_profile_objective_distribution.png": {
        "question": "Does the shape of the grade matter, beyond its thickness?",
        "x": "Grading profile",
        "y": "Objective value (a.u.)",
        "encoding": "Box shows the quartiles; every evaluated trial is drawn as a jittered point.",
        "data": _OBSERVED,
        "read": "Overlapping boxes mean the profile shape is not resolved by the trials run so far.",
        "limits": "Bayesian optimization does not sample categories evenly — it deliberately spends more trials on the shape it currently believes in, so these groups have unequal and non-random sizes. This is not a controlled comparison; Demo 12 Stage 3 is.",
    },
    "bo_parameter_sampling_by_iteration.png": {
        "question": "Did the search move as it learned?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the BO iteration.",
        "data": _OBSERVED,
        "read": "Early (dark) points spread out; later (light) points concentrate. That contraction is the visual signature of exploitation.",
        "limits": "Includes pending and failed trials, which have parameters but no objective.",
    },
    "bo_surrogate_mean_asymmetry_vs_grading_thickness.png": {
        "question": "What does the model believe the response is, across a plane it has not fully sampled?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the predicted posterior mean; open circles are evaluated trials.",
        "data": _SURROGATE,
        "read": "The mesh is a belief, not a measurement. Trust it near the evaluated points and treat it as a hypothesis far from them.",
        "limits": "Remaining parameters are held at the values recorded in bo.surrogate_slices.fixed_values in demo.yaml and repeated in the CSV. A different slice can look completely different.",
    },
    "bo_surrogate_uncertainty_asymmetry_vs_grading_thickness.png": {
        "question": "Where is the model still unsure?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the predicted standard error; open circles are evaluated trials.",
        "data": _SURROGATE,
        "read": "Uncertainty collapses around evaluated points and grows away from them. Bright regions are where another trial would teach the model the most.",
        "limits": "Standard error of the surrogate, not an experimental error bar. It says nothing about how accurate the underlying nextnano calculation is.",
    },
    "bo_acquisition_function_asymmetry_vs_grading_thickness.png": {
        "question": "Where would an improvement-seeking rule sample next?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is expected improvement; open circles are evaluated trials.",
        "data": _SURROGATE,
        "read": "Peaks sit where the mean is high, the uncertainty is large, or both — that balance is what exploration versus exploitation means in practice.",
        "limits": "This is analytic expected improvement recomputed from Ax's posterior mean and standard error on the slice. Ax's own generation step optimizes a Monte-Carlo log-noisy-EI acquisition over the full space, so this surface is an interpretable stand-in and not a replay of Ax's internal decision.",
    },
    "bo_surrogate_mean_barrier_vs_grading_thickness.png": {
        "question": "What does the model believe about the barrier–grading plane?",
        "x": "Central barrier thickness (nm)",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the predicted posterior mean; open circles are evaluated trials.",
        "data": _SURROGATE,
        "read": "As for the asymmetry–grading mean surface.",
        "limits": "Fixed values for the other parameters are recorded in the CSV and in demo.yaml.",
    },
    "bo_surrogate_uncertainty_barrier_vs_grading_thickness.png": {
        "question": "Where is the model unsure in the barrier–grading plane?",
        "x": "Central barrier thickness (nm)",
        "y": "Grading thickness (nm)",
        "encoding": "Colour is the predicted standard error; open circles are evaluated trials.",
        "data": _SURROGATE,
        "read": "As for the asymmetry–grading uncertainty surface.",
        "limits": "Surrogate uncertainty only.",
    },
    "bo_peak_chi2_vs_detuning_pareto.png": {
        "question": "Must a strong structure be mistuned?",
        "x": "|Detuning from 1550 nm| (nm)",
        "y": "Peak |χ²| (a.u.)",
        "encoding": "Colour is the response at 1550 nm.",
        "data": _OBSERVED,
        "read": "The upper-left corner is the ideal: strong and on target. Points forming a frontier from lower-left to upper-right are the real tradeoff.",
        "limits": "Nondominance here is over two objectives only; the tabulated Pareto set may use more.",
    },
    "bo_chi2_1550_vs_peak_chi2.png": {
        "question": "Is the telecom response limited by strength or by tuning?",
        "x": "Peak |χ²| (a.u.)",
        "y": "|χ²| at 1550 nm (a.u.)",
        "encoding": "Colour is the absolute detuning.",
        "data": _OBSERVED,
        "read": "Points near the diagonal are well tuned. Points far below it are strong structures wasting their strength at the wrong wavelength.",
        "limits": "Both axes are relative units on the same scale, so the diagonal is meaningful; neither is calibrated to pm/V.",
    },
    "bo_chi2_1550_vs_boundary_probability.png": {
        "question": "Is the optimizer being rewarded for badly confined states?",
        "x": "Boundary probability",
        "y": "|χ²| at 1550 nm (a.u.)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "A rising trend to the right is the warning sign: it means the largest responses come from states leaking to the domain edge, which is a numerical artifact and not a design.",
        "limits": "The constraint bound is applied by Ax separately; this plot shows the raw relationship including rejected points.",
    },
    "bo_chi2_1550_vs_state_tracking_confidence.png": {
        "question": "Are the best-scoring designs the ones the tracker is least sure about?",
        "x": "State-tracking confidence",
        "y": "|χ²| at 1550 nm (a.u.)",
        "encoding": "Marker shape is the grading profile.",
        "data": _OBSERVED,
        "read": "High response at low confidence is the Demo 11 failure mode reappearing: an apparent gain produced by states swapping labels through an avoided crossing.",
        "limits": "Confidence is an overlap against the nearest evaluated neighbour, so it depends on how densely that region was sampled.",
    },
    "bo_nonlinear_strength_vs_robustness_pareto.png": {
        "question": "Does the strongest design survive fabrication error?",
        "x": "Robustness score",
        "y": "|χ²| at 1550 nm (a.u.)",
        "encoding": "Colour is the peak response.",
        "data": _OBSERVED,
        "read": "Upper-right is both strong and tolerant. A steep frontier means robustness is expensive.",
        "limits": "Robustness is only defined for designs that went through the Stage 5 perturbation study; other trials have no score and are absent.",
    },
    "bo_parameter_importance.png": {
        "question": "Which parameter does the fitted model think matters most?",
        "x": "Parameter",
        "y": "First-order Sobol index",
        "encoding": "One bar per parameter.",
        "data": "Model-derived — a property of the fitted Ax surrogate, not of the physics.",
        "read": "Larger magnitude means the surrogate's prediction changes more with that parameter over the search space.",
        "limits": "Only valid once a surrogate exists and only as good as its fit; Ax reports poor cross-validation for small trial counts. It is a sensitivity of a model, and it is not a claim about causal physical importance.",
    },
    "bo_partial_dependence_asymmetry.png": {
        "question": "How does the model's prediction vary with asymmetry alone?",
        "x": "Quantum-well asymmetry, s",
        "y": "Objective value (a.u.)",
        "encoding": "Line is the surrogate mean, band is ±1 standard error, dark points are evaluated trials.",
        "data": _SURROGATE,
        "read": "Compare line and points: agreement means the one-dimensional summary is fair, disagreement means interactions dominate.",
        "limits": "Other parameters are held fixed at the recorded slice values — this is a slice, not a true marginal partial dependence averaged over the data.",
    },
    "bo_partial_dependence_barrier_thickness.png": {
        "question": "How does the model's prediction vary with barrier thickness alone?",
        "x": "Central barrier thickness (nm)",
        "y": "Objective value (a.u.)",
        "encoding": "Line is the surrogate mean, band is ±1 standard error, dark points are evaluated trials.",
        "data": _SURROGATE,
        "read": "As above.",
        "limits": "Slice at fixed values, as above.",
    },
    "bo_partial_dependence_grading_thickness.png": {
        "question": "How does the model's prediction vary with grading thickness alone?",
        "x": "Grading thickness (nm)",
        "y": "Objective value (a.u.)",
        "encoding": "Line is the surrogate mean, band is ±1 standard error, dark points are evaluated trials.",
        "data": _SURROGATE,
        "read": "As above. Under the hierarchical encoding this slice is the graded branch only; abrupt designs are a separate branch with no grading thickness at all.",
        "limits": "Slice at fixed values, as above.",
    },
    "bo_grading_profile_effect.png": {
        "question": "Which grading shape produced the best objective on average?",
        "x": "Grading profile",
        "y": "Mean objective value (a.u.)",
        "encoding": "One bar per profile; the CSV also carries the best and worst value and the trial count.",
        "data": _OBSERVED,
        "read": "Use the trial counts in the CSV before reading anything into a difference between bars.",
        "limits": "Unequal, non-random group sizes — see the caveat on the profile distribution plot.",
    },
    "bo_valid_and_invalid_trials_by_iteration.png": {
        "question": "Is the optimizer wasting solver time in invalid regions?",
        "x": "BO iteration",
        "y": "Trials",
        "encoding": "Stacked bars: valid, invalid, failed.",
        "data": _OBSERVED,
        "read": "Healthy behaviour is a large invalid fraction early that shrinks as the constraint model learns the feasible region.",
        "limits": "Iteration 0 is the initial Sobol design, which has no model and is expected to be the worst-behaved.",
    },
    "bo_failure_reason_counts.png": {
        "question": "What actually rejects designs in this study?",
        "x": "Rejection or failure reason",
        "y": "Trials",
        "encoding": "One bar per named reason; a trial with several violations is counted under each.",
        "data": _OBSERVED,
        "read": "A single dominant reason usually means a search bound should be reconsidered rather than a tolerance loosened.",
        "limits": "Mechanical failures are counted once as `mechanical_failure`; their detailed cause is in the invalid-and-failed table.",
    },
    "bo_boundary_probability_by_trial.png": {
        "question": "Are the states staying confined as the search moves?",
        "x": "Trial number",
        "y": "Boundary probability (log scale)",
        "encoding": "Dashed line is the configured constraint bound.",
        "data": _OBSERVED,
        "read": "Points climbing toward the bound mean the search is drifting into geometries the simulation domain cannot hold.",
        "limits": "Maximum over bound states; a single leaking state sets the value.",
    },
    "bo_state_tracking_confidence_by_trial.png": {
        "question": "Can the tracker still follow the states the optimizer is asking about?",
        "x": "Trial number",
        "y": "State-tracking confidence",
        "encoding": "Dashed line is the configured minimum.",
        "data": _OBSERVED,
        "read": "Dips coincide with avoided crossings or with jumps into unsampled regions.",
        "limits": "Each trial is compared to its nearest evaluated neighbour, so confidence is partly a measure of how isolated the trial was.",
    },
    "bo_validity_map_asymmetry_vs_grading_thickness.png": {
        "question": "Where in the design space are the valid designs?",
        "x": "Quantum-well asymmetry, s",
        "y": "Grading thickness (nm)",
        "encoding": "Blue circle valid, orange cross invalid, red square failed.",
        "data": _OBSERVED,
        "read": "Contiguous invalid regions are physical; scattered invalid points among valid ones usually mean a marginal tolerance.",
        "limits": "Projection of four dimensions onto two.",
    },
    "baseline_and_top_bo_designs_chi2_spectra.png": {
        "question": "How does the shape of the response change between the reference and the best designs?",
        "x": "Fundamental wavelength (nm)",
        "y": "Normalized |χ²| (a.u.)",
        "encoding": "One line per design; dashed vertical line is 1550 nm.",
        "data": _OBSERVED,
        "read": "Compare both the height and the position of the resonance; a better objective can come from either.",
        "limits": "Relative units, normalized for shape comparison. Never labelled pm/V.",
    },
    "baseline_and_best_bo_composition_profiles.png": {
        "question": "What did the optimizer actually change about the structure?",
        "x": "Position (nm)",
        "y": "Al fraction, x",
        "encoding": "One line per design.",
        "data": "Requested composition profile, as rendered into the nextnano input.",
        "read": "The realized profile from the solver's own alloy output is validated separately per trial, exactly as in Demo 12 Stage 1.",
        "limits": "This is the requested profile. A licensed run must confirm the realized one before any conclusion depends on the grade shape.",
    },
    "baseline_and_best_bo_conduction_band_edges.png": {
        "question": "How does the electron potential differ between reference and best?",
        "x": "Position (nm)",
        "y": "Energy (eV)",
        "encoding": "One line per design.",
        "data": "Solver output — requires a licensed run.",
        "read": "Grading rounds the well corners; that rounding is the mechanism behind any change in the matrix elements.",
        "limits": "Empty without licensed nextnano output.",
    },
    "baseline_and_best_bo_valence_band_edges.png": {
        "question": "How does the hole potential differ between reference and best?",
        "x": "Position (nm)",
        "y": "Energy (eV)",
        "encoding": "One line per design.",
        "data": "Solver output — requires a licensed run.",
        "read": "Electron and hole potentials respond differently to the same grade, which is what shifts their centroid separation.",
        "limits": "Empty without licensed nextnano output.",
    },
    "baseline_and_best_bo_electron_wavefunctions.png": {
        "question": "Did the electron states redistribute between the wells?",
        "x": "Position (nm)",
        "y": "Envelope amplitude (a.u.)",
        "encoding": "One line per state per design.",
        "data": "Solver output — requires a licensed run.",
        "read": "Amplitudes, not probability densities, and not offset onto their eigenenergies. The sign is physical here because the tracker aligns it along a branch.",
        "limits": "Empty without licensed nextnano output.",
    },
    "baseline_and_best_bo_hole_wavefunctions.png": {
        "question": "Did the hole states redistribute between the wells?",
        "x": "Position (nm)",
        "y": "Envelope amplitude (a.u.)",
        "encoding": "One line per state per design.",
        "data": "Solver output — requires a licensed run.",
        "read": "Compare against the electron envelopes: χ² needs both, and cancellation between them is the known failure mode from the earlier replication work.",
        "limits": "Empty without licensed nextnano output.",
    },
    "baseline_and_best_bo_state_localization.png": {
        "question": "Where does the ground state actually sit in each design?",
        "x": "Region",
        "y": "Probability",
        "encoding": "Grouped bars, one group per region, one bar per design.",
        "data": _OBSERVED,
        "read": "A large boundary bar invalidates the design regardless of its χ².",
        "limits": "Ground state only; per-state values are in the localization table.",
    },
    "baseline_and_best_bo_transition_energies.png": {
        "question": "Which transitions moved, and by how much?",
        "x": "Transition",
        "y": "Transition energy (eV)",
        "encoding": "Grouped bars, one bar per design.",
        "data": _OBSERVED,
        "read": "The e1–hh1 energy sets the two-photon resonance; a change here is what retunes the spectrum.",
        "limits": "Tracked-label transitions, not raw energy order.",
    },
    "top_bo_designs_chi2_spectra.png": {
        "question": "Do the best designs agree on a resonance, or are they different solutions?",
        "x": "Fundamental wavelength (nm)",
        "y": "Normalized |χ²| (a.u.)",
        "encoding": "One line per top design.",
        "data": _OBSERVED,
        "read": "Several distinct resonance positions with similar objectives means the problem has multiple optima, and the ranking between them is not robust.",
        "limits": "Relative units.",
    },
    "bo_vs_random_search_best_objective.png": {
        "question": "Did Bayesian optimization beat random sampling at equal cost?",
        "x": "Evaluations",
        "y": "Best objective value (a.u.)",
        "encoding": "One step line per method.",
        "data": _OBSERVED,
        "read": "Compare at equal evaluation counts, not at the end of the run. The area between the curves is the solver time saved.",
        "limits": "A single random seed is a single sample. Rerun with several seeds before making a quantitative efficiency claim.",
    },
    "bo_vs_grid_search_best_objective.png": {
        "question": "Did Bayesian optimization beat the Demo 12 grid at equal cost?",
        "x": "Evaluations",
        "y": "Best objective value (a.u.)",
        "encoding": "One step line per method.",
        "data": _OBSERVED,
        "read": "The grid curve rises in its own traversal order, which is a real property of how a grid is actually run.",
        "limits": "The grid's ordering is a design choice; a different traversal gives a different curve. The end point is order-independent, the path is not.",
    },
    "bo_random_grid_evaluations_to_best_known_result.png": {
        "question": "How many nextnano runs did each method need?",
        "x": "Search method",
        "y": "Evaluations",
        "encoding": "One bar per method; zero means the threshold was never reached.",
        "data": _OBSERVED,
        "read": "This is the number that decides whether Bayesian optimization pays for itself in licensed solver time.",
        "limits": "Threshold is a configured fraction of the best known value in the replay pool, and the pool bounds what any method can find.",
    },
    "demo11_demo12_demo13_best_chi2_spectra.png": {
        "question": "Did the optimization improve on the earlier demos?",
        "x": "Fundamental wavelength (nm)",
        "y": "Normalized |χ²| (a.u.)",
        "encoding": "One line per demo's best design; dashed vertical line is 1550 nm.",
        "data": _OBSERVED,
        "read": "This is the headline comparison of the whole demo. Read it with the comparison table, which carries the QC status of each design.",
        "limits": "All three curves must come from the same physics settings to be comparable; the comparison table records whether they do.",
    },
    "paper_figure2d_simulation_comparison_full_range.png": {
        "question": "Does the simulated lineshape resemble the published one?",
        "x": "Fundamental wavelength (nm)",
        "y": "Normalized |χ²| (a.u.)",
        "encoding": "One line per source, including the digitized paper curve.",
        "data": "Mixed — simulated curves are computed; the paper curve is eye-digitized.",
        "read": "Compare the position and relative shape of features only.",
        "limits": "The digitized curve carries an unquantified reading error and is a visual reference, never a target or a validation ground truth. See PAPER_COMPARISON_GUIDE.md.",
    },
    "paper_figure2d_simulation_comparison_telecom_range.png": {
        "question": "Does the agreement hold in the telecom band specifically?",
        "x": "Fundamental wavelength (nm)",
        "y": "Normalized |χ²| (a.u.)",
        "encoding": "As above, restricted to the telecom window.",
        "data": "Mixed — as above.",
        "read": "This is the window the optimization actually targets.",
        "limits": "As above.",
    },
    "paper_measured_sh_intensity_comparison.png": {
        "question": "How does the measured second-harmonic intensity behave?",
        "x": "Fundamental wavelength (nm)",
        "y": "Measured SH intensity (a.u.)",
        "encoding": "One line per measured dataset.",
        "data": "Measured, if any measured dataset is configured.",
        "read": "Kept on its own axes deliberately: measured SH intensity depends on the pump, the geometry and the collection efficiency, and is not proportional to a simulated χ².",
        "limits": "Empty unless paper_comparison.measured_intensity_csv is configured. Never plotted on the same axis as a simulated susceptibility.",
    },
}


def _header(title: str, cfg: Mapping[str, Any]) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Demo: `{cfg.get('demo_id')}`  ",
        f"Generated: {dt.datetime.now(dt.timezone.utc).date().isoformat()} (UTC)  ",
        "Generated by `report13.py`; edit that file, not this one.",
        "",
    ]


# ---------------------------------------------------------------------------
# guides
# ---------------------------------------------------------------------------


def plots_guide(cfg: Mapping[str, Any]) -> str:
    fixed = (cfg.get("bo") or {}).get("surrogate_slices", {}).get("fixed_values", {})
    lines = _header("Demo 13 plots guide", cfg)
    lines += [
        "Figures in this demo carry axis labels, tick labels, a concise legend and",
        "nothing else. No titles, no captions, no interpretation inside the frame.",
        "Everything explanatory is here.",
        "",
        "Two conventions run through the whole set:",
        "",
        "- **observed** data is drawn as markers and is never smoothed;",
        "- **surrogate-predicted** data is drawn as a continuous mesh or line with the",
        "  evaluated points overlaid, so a prediction can never be mistaken for a",
        "  measurement.",
        "",
        "Every figure that had data to draw is written as `.png` and `.pdf`. A figure",
        "with no data becomes a labelled PNG placeholder rather than a missing file, so",
        "an absent `.png` is always a bug and never 'no licence on this machine'.",
        "Every figure has a CSV of exactly the plotted numbers at",
        "`plot_data/<same base name>.csv`, written even when the figure is a placeholder.",
        "",
        "Two-dimensional surrogate slices hold the remaining parameters fixed at:",
        "",
    ]
    lines += [f"- `{name}` = `{value}`" for name, value in dict(fixed).items()] or ["- (none configured)"]
    lines += ["", "---", ""]
    # The surrogate figures are drawn over the *search-space* grading coordinate,
    # which under `parameterization: fraction` is dimensionless. Their guide
    # entries say "Grading thickness (nm)" as a static string, so leaving them
    # alone would have the prose contradict the axis the code now draws.
    _, grading_label = plots13.grading_axis(cfg)
    for filename, short in plots13.PLOT_SET:
        entry = PLOT_GUIDE.get(filename)
        lines += [f"## `{filename}`", ""]
        if entry is None:  # pragma: no cover - guarded by a test
            lines += [f"_{short}_ — no guide entry; this is a bug.", ""]
            continue
        y_axis = entry["y"]
        if entry["data"] is _SURROGATE and y_axis == plots13.AXIS["grading"]:
            y_axis = (
                f"{grading_label} — the realized thickness in nm is carried in the "
                "CSV as `realized_grading_thickness_nm`"
            )
        lines += [
            f"**Question.** {entry['question']}",
            "",
            f"- x-axis: {entry['x']}",
            f"- y-axis: {y_axis}",
            f"- colour / marker / line: {entry['encoding']}",
            f"- data type: {entry['data']}",
            f"- CSV: `plot_data/{Path(filename).stem}.csv`",
            "",
            f"**How to read it.** {entry['read']}",
            "",
            f"**Limitations.** {entry['limits']}",
            "",
        ]
    return "\n".join(lines)


def tables_guide(cfg: Mapping[str, Any]) -> str:
    constraints = (cfg.get("bo") or {}).get("outcome_constraints") or {}
    lines = _header("Demo 13 tables guide", cfg)
    lines += [
        "Every table is a projection of the append-only trial ledger, so all of them",
        "can be regenerated at any time without touching the optimization history.",
        "Every table is CSV; the summary tables are also Markdown and JSON. Each CSV",
        "has a `<name>.units.json` sidecar giving the unit of every column.",
        "",
        "## Units used in this demo",
        "",
        "| unit | meaning |",
        "|---|---|",
        "| `a.u. (relative |χ²|)` | Demo 11 Eq. 2 relative susceptibility: a lineshape and a trend with no absolute scale. **Never** pm/V. |",
        "| `nm` | length or wavelength |",
        "| `eV`, `meV` | energy |",
        "| `probability` | integrated |ψ|² over a region, in [0, 1] |",
        "| `overlap in [0,1]` | normalized envelope overlap used by state tracking |",
        "| `0 or 1` | a boolean validity flag, in numeric form because Ax constrains on it |",
        "",
        "## Validity criteria used for filtering",
        "",
        "A trial is **valid** when it completed, passed every Demo 11 physical check,",
        "returned the expected number of states, passed the origin-independence test,",
        "and satisfied the configured bounds:",
        "",
    ]
    lines += [f"- `{name}`: `{value}`" for name, value in dict(constraints).items()]
    lines += [
        "",
        "A trial that **failed mechanically** (solver crash, missing output) has no",
        "objective at all and is reported to Ax through `mark_trial_failed`. A trial",
        "that ran but is invalid keeps every metric it produced and is rejected by the",
        "outcome constraints. A valid design with a near-zero response is neither: it",
        "is a real observation, flagged `valid_low_response`.",
        "",
        "---",
        "",
    ]
    for name, meaning in tables13.TABLE_CATALOGUE.items():
        formats = "CSV, Markdown, JSON" if name in tables13.SUMMARY_TABLES else "CSV"
        lines += [
            f"## `{name}.csv`",
            "",
            f"- one row = {meaning}",
            f"- formats: {formats}",
            f"- units: `tables/{name}.units.json`",
            f"- intended use: {_TABLE_USE.get(name, 'analysis of the completed run')}",
            "",
        ]
    return "\n".join(lines)


_TABLE_USE: Mapping[str, str] = {
    "bo_all_trials_parameters_and_outcomes": "the single source of truth for the run; every other table is derived from it",
    "bo_trial_input_parameters": "checking what geometry each trial actually simulated",
    "bo_trial_nonlinear_optical_outputs": "comparing designs on χ² alone",
    "bo_trial_electronic_structure_outputs": "diagnosing *why* a design's χ² changed",
    "bo_trial_state_localization_and_tracking": "checking that a good score is not a state-labelling artifact",
    "bo_trial_quality_control_results": "auditing whether a result may be used at all",
    "bo_best_objective_so_far_by_iteration": "deciding whether more BO iterations are worth licensed solver time",
    "bo_top_ranked_valid_designs": "choosing candidates for Stage 5 validation; the `validated` column is False until that runs",
    "bo_invalid_and_failed_trials": "understanding what the search space is doing wrong",
    "demo11_demo12_demo13_best_design_comparison": "the final claim of the demo; read the QC columns before the χ² columns",
    "bo_generated_candidates_by_iteration": "auditing the proposal lifecycle, including duplicates the deduplicator caught",
    "bo_surrogate_predictions_selected_parameter_slices": "reproducing the surrogate figures exactly",
    "bo_acquisition_values_for_proposed_candidates": "seeing how much improvement Ax expected from each proposal",
    "bo_parameter_importance": "ranking parameters for a follow-up study, with the model caveat attached",
    "bo_pareto_optimal_designs": "multi-objective selection without collapsing to one number",
    "bo_top_designs_local_validation_results": "deciding whether an Ax optimum survives refinement",
    "bo_top_designs_fabrication_robustness": "deciding whether an optimum survives fabrication error",
    "bo_random_grid_search_efficiency_comparison": "justifying Bayesian optimization against cheaper baselines",
    "bo_run_plan_and_case_counts": "confirming the YAML iteration count produced the intended budget",
    "bo_demo12_warm_start_provenance": "auditing exactly which Demo 12 results entered the optimization, and which were rejected and why",
    "bo_search_space_definition": "recording the exact search space of this run",
}


def ax_guide(cfg: Mapping[str, Any]) -> str:
    bo = cfg["bo"]
    counts = design13.expected_evaluation_counts(cfg)
    lines = _header("Demo 13 Ax optimization guide", cfg)
    lines += [
        "This guide is written for a researcher who knows the physics and is meeting",
        "Bayesian optimization for the first time.",
        "",
        "## What Bayesian optimization is doing",
        "",
        "Every nextnano trial is expensive, so the optimizer does not sample the space",
        "on a grid. Instead it keeps a *surrogate model* — a Gaussian process — that",
        "predicts, for any design it has not tried, both a mean response and an",
        "uncertainty. An *acquisition function* turns that pair into a single score for",
        "'how much would I learn or gain by running this design next', and the next",
        "candidate is the design that maximizes it.",
        "",
        "The consequence worth internalizing: **the optimizer sometimes proposes a",
        "design it expects to be mediocre.** That is exploration, and it is how the",
        "model stops believing a local maximum is the global one.",
        "",
        "## The two phases of a run",
        "",
        f"1. **Initialization** — `bo.num_initial_trials` = {counts['num_initial_trials']}",
        "   quasi-random (Sobol) designs. There is no model yet; these trials exist to",
        "   build one. Ax reports these as generation node `Sobol`.",
        f"2. **Bayesian iterations** — `bo.num_iterations` = {counts['num_iterations']}",
        f"   rounds of `bo.batch_size` = {counts['batch_size']} candidate(s) each, chosen",
        "   by the fitted model. Ax reports these as generation node `MBM`.",
        "",
        f"Total expected nextnano evaluations = initial + iterations × batch =",
        f"**{counts['expected_maximum_new_solver_runs']}**. Changing `num_iterations` in",
        "`demo.yaml` changes this number and the length of the run, and nothing else",
        "needs editing — the count is read in one place and hardcoded nowhere.",
        "",
        "## The objective",
        "",
        f"- current mode: `{bo.get('optimization_mode')}`",
        f"- Mode A `target_wavelength` — maximize `relative_chi2_at_target_wavelength_abs`, the",
        f"  response exactly at {bo.get('target_wavelength_nm')} nm. The default.",
        "- Mode B `intrinsic_peak` — maximize `relative_peak_chi2_abs`, the response at whatever",
        "  wavelength that structure happens to resonate at. Answers a different",
        "  question: which structure is intrinsically strongest.",
        "- Mode C `multi_objective` — Ax's multi-objective optimization over peak",
        "  response, target response, detuning and robustness, returning a Pareto set",
        "  rather than one winner.",
        "- `weighted_score` — an optional single number. Supported, but the individual",
        "  physical metrics stay visible in every table; the score never replaces them.",
        "",
        "## Outcome constraints",
        "",
        "Constraints are how a physically invalid design is rejected *without* lying to",
        "the optimizer about its objective. Ax models each constrained metric as well,",
        "and prefers candidates it believes will satisfy them:",
        "",
    ]
    for name, value in (bo.get("outcome_constraints") or {}).items():
        lines.append(f"- `{name}`: `{value}`")
    lines += [
        "",
        "There is a hard rule underneath this: a trial that failed *mechanically* — the",
        "solver crashed, output files are missing — is reported through",
        "`Client.mark_trial_failed` and is given no objective at all. Giving it an",
        "objective of zero would teach the model that a whole region of the design",
        "space is genuinely bad, when all that happened was a crash.",
        "",
        "## Categorical grading profiles",
        "",
        f"The search space encoding is `{bo['search_space'].get('encoding')}`.",
        "",
        "The problem being solved: an abrupt interface is the same physical structure",
        "no matter which profile label is attached to it, so a naive four-parameter",
        "space contains five different parameterizations of one structure — and would",
        "happily spend five licensed nextnano runs on them.",
        "",
        "- **hierarchical** (default) — a root choice `interface_mode` ∈ {abrupt,",
        f"  graded}}. Only the `graded` branch has `{design13.grading_parameter_name(cfg)}`",
        "  and `grading_profile` at all, so the duplicate cannot be expressed. Ax 1.3.1",
        "  requires such a space to be a tree, which is why the branch is on",
        "  `interface_mode` rather than directly on `grading_profile`.",
        "- **flat** — the plain four-parameter space. Duplicates are prevented instead",
        "  by canonicalization (`abrupt` ⇒ 0 nm; a sub-resolution thickness ⇒ abrupt)",
        "  and by a deduplication key at the configured tolerances.",
        "",
        "Both encodings canonicalize before anything is simulated, so a trial record",
        "means the same thing under either one.",
        "",
        "## Surrogate predictions and acquisition values",
        "",
        "`Client.predict` gives the posterior mean and standard error at any point;",
        "that is what the surrogate figures show. The acquisition *value* Ax reported",
        "for each proposal is recorded per trial from the generator run's metadata. The",
        "acquisition *surface* in the figures is analytic expected improvement",
        "recomputed from the posterior on a slice — an interpretable stand-in, not a",
        "replay of the Monte-Carlo acquisition Ax actually optimized.",
        "",
        "## Checkpointing and resume",
        "",
        "Two things are written after every generated and every completed trial:",
        "",
        "1. the **Ax snapshot** (`ax_experiment_snapshot.json`), written to a temporary",
        "   file and then renamed, so an interrupted write cannot truncate it;",
        "2. the **trial ledger** — one immutable JSON file per trial plus a JSONL index",
        "   — holding everything Ax does not store: input path, output directory, QC",
        "   verdict, failure reason, runtime, provenance.",
        "",
        "On resume, the snapshot is loaded and the ledger decides what is already done.",
        "A run that completed five of ten iterations continues at iteration six. A",
        "terminal ledger record is never rewritten; attempting it raises rather than",
        "silently losing history.",
        "",
        "## What Bayesian optimization does not tell you",
        "",
        "The highest objective in the table is a **proposed** optimum. It has not been",
        "checked for mesh convergence, state-count convergence, domain-padding",
        "sensitivity, or fabrication robustness. Stage 5 does that, and until it passes,",
        "the correct description is 'best trial so far', not 'the optimum'.",
        "",
    ]
    return "\n".join(lines)


def paper_guide(cfg: Mapping[str, Any]) -> str:
    paper = cfg.get("paper_comparison") or {}
    lines = _header("Demo 13 paper comparison guide", cfg)
    lines += [
        "## Where the paper curve comes from",
        "",
        f"- source: {paper.get('source')}",
        f"- digitized simulation curve: `{paper.get('digitized_simulation_csv')}`",
        f"- measured intensity dataset: `{paper.get('measured_intensity_csv')}`",
        "",
        "The paper curve was read off a published figure by eye. That carries an",
        "unquantified error in both axes — worse where the curve is steep, worse still",
        "near the axes limits — and it inherits every choice the original authors made",
        "about normalization and plotting.",
        "",
        "**It is therefore a visual reference only.** It is not used as an optimization",
        "target, not used as calibration data, and not used as validation ground truth.",
        "Nothing in the optimization loop reads it.",
        "",
        "## Normalized versus absolute χ²",
        "",
        f"Demo 13 runs Demo 11's Eq. 2 in `{(cfg.get('metric') or {}).get('mode')}` mode.",
        "That produces a **relative** susceptibility: the lineshape and the trend are",
        "meaningful, the absolute scale is not set. Axis labels therefore read",
        "`Normalized |χ²| (a.u.)`.",
        "",
        "`pm/V` appears nowhere in this demo's figures. Demo 11 does support a",
        "calibrated mode, in which one global factor is fitted to a single published",
        "value — but a curve calibrated to a paper cannot then be used to confirm that",
        "paper, so Demo 13 does not optimize in calibrated units and does not label its",
        "relative results with an absolute one.",
        "",
        "## Why measured SH intensity is not simulated χ²",
        "",
        "A measured second-harmonic intensity is proportional to |χ⁽²⁾|² and also to the",
        "pump intensity squared, the interaction length, the mode overlap, phase",
        "matching, absorption at both wavelengths, and the collection efficiency of the",
        "setup. None of those are in this calculation. Plotting the two on one axis",
        "would invite exactly the comparison that is not valid, so measured intensity",
        "gets its own figure: `paper_measured_sh_intensity_comparison.png`.",
        "",
        "## How the comparison is made",
        "",
        "Each simulated spectrum is normalized to its own maximum inside the plotted",
        "window, then drawn against the digitized curve on the same axes. What may be",
        "compared:",
        "",
        "- the **position** of resonant features;",
        "- the **relative shape** — how sharp, how asymmetric, how many peaks;",
        "- whether a feature exists at all.",
        "",
        "What may not be compared: absolute magnitudes, peak ratios to better than a",
        "visual impression, or anything at all in the wings where the digitization is",
        "least reliable.",
        "",
        "## What can and cannot be claimed",
        "",
        "Can: 'the simulated resonance falls within N nm of the published one', with N",
        "generously bounded; 'the simulated lineshape is qualitatively similar'.",
        "",
        "Cannot: 'this reproduces the paper'; 'the simulated χ² is X pm/V'; 'the",
        "optimized design is Y× better than the paper's', on the strength of digitized",
        "values.",
        "",
        f"Configured policy: {paper.get('claim_policy')}",
        "",
        "Note on filenames: the required figure set names the three-demo spectral",
        "comparison `demo11_demo12_demo13_best_chi2_spectra.png`; that is the file the",
        "specification also refers to as `demo11_demo12_demo13_chi2_spectra_comparison`.",
        "There is one such figure, under the first name.",
        "",
    ]
    return "\n".join(lines)


def work_laptop_guide(cfg: Mapping[str, Any]) -> str:
    counts = design13.expected_evaluation_counts(cfg)
    lines = _header("Demo 13 work-laptop run guide", cfg)
    lines += [
        "Every command below is implemented in this repository. Run them from the",
        "repository root in PowerShell on the licensed work laptop.",
        "",
        "## 1. Pull the code",
        "",
        "```powershell",
        "git pull",
        "```",
        "",
        "## 2. Activate the environment",
        "",
        "```powershell",
        "conda activate llm",
        "```",
        "",
        "## 3. Check that Ax is installed and pinned",
        "",
        "```powershell",
        "python -c \"import ax; print(ax.__version__)\"",
        "```",
        "",
        f"Expect `{cfg['bo'].get('required_ax_version')}`. If it is missing or older than",
        f"`{cfg['bo'].get('minimum_ax_version')}`, install the pin:",
        "",
        "```powershell",
        "pip install \"ax-platform==" + str(cfg["bo"].get("required_ax_version")) + "\"",
        "```",
        "",
        "## 4. Verify nextnano++ and the environment, without running anything",
        "",
        "```powershell",
        "python .\\nextnano\\demos\\13_ax_bayesian_optimization_graded_acqw\\run_demo13.py --check",
        "```",
        "",
        "This prints the resolved solver path, the Ax version, the search space, and the",
        "planned evaluation budget, and exits without generating or running a trial.",
        "",
        "## 5. Run the solver-free tests",
        "",
        "```powershell",
        "python -m pytest .\\nextnano\\tests\\test_demo13_ax_bayesian_optimization.py -q",
        "```",
        "",
        "## 6. Run the synthetic smoke test (no solver, no licence)",
        "",
        "Set `workflow.mode: synthetic_smoke_test` in `demo.yaml`, then:",
        "",
        "```powershell",
        "python .\\nextnano\\demos\\13_ax_bayesian_optimization_graded_acqw\\run_demo13.py",
        "```",
        "",
        "## 7. Turn the solver on",
        "",
        "In `demo.yaml` set:",
        "",
        "```yaml",
        "simulation:",
        "  run_solver: true",
        "workflow:",
        "  mode: closed_loop",
        "```",
        "",
        "## 8. Run the small licensed smoke study first (Stage 3)",
        "",
        "Set `bo.num_initial_trials: 3`, `bo.num_iterations: 2`, `bo.batch_size: 1`,",
        "then:",
        "",
        "```powershell",
        "python .\\nextnano\\demos\\13_ax_bayesian_optimization_graded_acqw\\run_demo13.py",
        "```",
        "",
        "That is 5 nextnano evaluations. Inspect the validation report, the realized",
        "alloy profiles, and the QC table before going further.",
        "",
        "## 9. Run the configured study (Stage 4)",
        "",
        f"Restore `bo.num_initial_trials: {counts['num_initial_trials']}` and",
        f"`bo.num_iterations: {counts['num_iterations']}`",
        f"({counts['expected_maximum_new_solver_runs']} evaluations), then:",
        "",
        "```powershell",
        "python .\\nextnano\\demos\\13_ax_bayesian_optimization_graded_acqw\\run_demo13.py",
        "```",
        "",
        "## 10. Resume an interrupted run",
        "",
        "Exactly the same command. `workflow.resume: true` is the default; the Ax",
        "snapshot and the trial ledger are reloaded and the run continues from the",
        "first unfinished iteration.",
        "",
        "```powershell",
        "python .\\nextnano\\demos\\13_ax_bayesian_optimization_graded_acqw\\run_demo13.py",
        "```",
        "",
        "To raise the budget mid-study, increase `bo.num_iterations` and rerun the same",
        "command; completed iterations are not repeated.",
        "",
        "## 11. Regenerate tables, plots and guides from existing results",
        "",
        "Set `workflow.mode: analyze_existing_results`, then rerun. No solver is called.",
        "",
        "## 12. Validate the top designs (Stage 5)",
        "",
        "Set `workflow.mode: validate_top_designs`, then rerun. This runs local",
        "refinement, mesh, state-count, padding and fabrication-perturbation cases",
        "around the best designs and writes the two validation tables.",
        "",
        "## 13. Package the results for transfer",
        "",
        "```powershell",
        "python .\\nextnano\\scripts\\bundle_results.py --include-plots",
        "```",
        "",
        "## Transferring an experiment between machines",
        "",
        "The optimization state is the experiment directory named by",
        f"`workflow.experiment_state_dir` (`{(cfg.get('workflow') or {}).get('experiment_state_dir')}`)",
        "under the results root. Copy that whole directory to move a study between the",
        "home and work laptops: it holds the Ax snapshot, the immutable trial ledger,",
        "and the YAML snapshot the experiment was created with.",
        "",
    ]
    return "\n".join(lines)


def results_overview(cfg: Mapping[str, Any], summary: Mapping[str, Any] | None = None) -> str:
    summary = dict(summary or {})
    counts = design13.expected_evaluation_counts(cfg)
    bo = cfg["bo"]
    lines = _header("Demo 13 results overview", cfg)
    licensed = bool(summary.get("licensed_results_present", False))
    lines += [
        "## Goal",
        "",
        "Search the Demo 12 graded asymmetric coupled-quantum-well design space with",
        "Bayesian optimization instead of a structured grid, and find designs with a",
        f"larger |χ²| at {bo.get('target_wavelength_nm')} nm that also survive quality",
        "control.",
        "",
        "## Parameter space",
        "",
        "| parameter | type | range or values | unit |",
        "|---|---|---|---|",
    ]
    for spec in design13.search_space_specs(cfg):
        row = spec.as_row()
        extent = (
            f"{row['lower']} … {row['upper']}"
            if row["type"] == "range"
            else str(row["values"])
        )
        lines.append(
            f"| `{row['parameter']}` | {row['type']} | {extent} | "
            f"{tables13.unit_for('parameter_' + str(row['parameter']))} |"
        )
    lines += [
        "",
        f"Search-space encoding: `{bo['search_space'].get('encoding')}`. "
        f"Optional extensions enabled: "
        f"{', '.join(design13.enabled_optional_parameters(cfg)) or 'none'}.",
        "",
        "## Objective and constraints",
        "",
        f"- mode: `{bo.get('optimization_mode')}`",
        f"- objective: {summary.get('ax_objective_string', 'see AX_OPTIMIZATION_GUIDE.md')}",
        "- constraints:",
    ]
    for name, value in (bo.get("outcome_constraints") or {}).items():
        lines.append(f"  - `{name}`: `{value}`")
    lines += [
        "",
        "## Budget",
        "",
        f"- initial trials: {counts['num_initial_trials']}",
        f"- BO iterations: {counts['num_iterations']}",
        f"- batch size: {counts['batch_size']}",
        f"- expected maximum new solver runs: "
        f"**{counts['expected_maximum_new_solver_runs']}** "
        f"(initial + iterations × batch)",
        "",
        "## Current state of this run",
        "",
    ]
    if not licensed:
        lines += [
            "**No licensed nextnano++ results are present in this bundle.** Inputs were",
            "generated, the search space and the optimization loop were exercised, and",
            "the table, figure and guide contract was produced — but no physical result",
            "has been computed, and nothing here may be read as one.",
            "",
        ]
    else:
        lines += [
            f"- completed trials: {summary.get('completed_trials')}",
            f"- valid trials: {summary.get('valid_trials')}",
            f"- failed trials: {summary.get('failed_trials')}",
            f"- best valid objective: {summary.get('best_objective')}",
            f"- best trial index: {summary.get('best_trial_index')}",
            "",
        ]
    lines += [
        "## Best current design",
        "",
    ]
    best = summary.get("best_design")
    if not best:
        lines += ["No valid design has been computed in this bundle.", ""]
    else:
        lines += ["| quantity | value |", "|---|---|"]
        lines += [f"| `{name}` | {value} |" for name, value in dict(best).items()]
        lines += [""]
    lines += [
        "## Has it been validated?",
        "",
        f"**{'Yes' if summary.get('stage5_validated') else 'No'}.** "
        + (
            "Stage 5 local refinement, mesh, state-count and padding checks have been "
            "applied; see the validation tables."
            if summary.get("stage5_validated")
            else "The highest Ax objective is a *proposed* optimum. Until Stage 5 local "
            "refinement, mesh convergence, state-count convergence, domain-padding and "
            "fabrication-perturbation checks pass, it must be described as the best "
            "trial so far and not as the optimum."
        ),
        "",
        "## Comparison with Demos 11 and 12",
        "",
        "The full comparison is in",
        "`tables/demo11_demo12_demo13_best_design_comparison.csv` and in the figure",
        "`plots/demo11_demo12_demo13_best_chi2_spectra.png`. It compares, on identical",
        "columns: input geometry, grading profile and thickness, asymmetry, barrier",
        "thickness, peak χ², peak wavelength, χ² at 1550 nm, detuning, boundary",
        "probability, state-tracking confidence, robustness, QC status, and the number",
        "of nextnano evaluations each approach needed.",
        "",
    ]
    verdict = summary.get("verdict")
    if verdict:
        lines += ["### Verdict", "", str(verdict), ""]
    else:
        lines += [
            "### Verdict",
            "",
            "Not available: no licensed comparison has been computed in this bundle.",
            "The four possible outcomes the final report must choose between are a",
            "stronger intrinsic design, a stronger 1550 nm design, a better",
            "wavelength-matched design, a more robust design, or an apparent improvement",
            "that did not survive validation.",
            "",
        ]
    lines += [
        "## Where to look next",
        "",
        "- `PLOTS_GUIDE.md` — every figure, what it answers, and its limitations",
        "- `TABLES_GUIDE.md` — every table, its rows, columns and units",
        "- `AX_OPTIMIZATION_GUIDE.md` — how the search works, for a first-time reader",
        "- `PAPER_COMPARISON_GUIDE.md` — what may and may not be claimed against the paper",
        "- `WORK_LAPTOP_RUN_GUIDE.md` — exact commands for the licensed machine",
        "",
    ]
    return "\n".join(lines)


def write_guides(
    target_dir: Path, cfg: Mapping[str, Any], summary: Mapping[str, Any] | None = None
) -> list[Path]:
    """Write all six guides into ``target_dir``."""

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, builder in (
        ("RESULTS_OVERVIEW.md", lambda: results_overview(cfg, summary)),
        ("PLOTS_GUIDE.md", lambda: plots_guide(cfg)),
        ("TABLES_GUIDE.md", lambda: tables_guide(cfg)),
        ("AX_OPTIMIZATION_GUIDE.md", lambda: ax_guide(cfg)),
        ("PAPER_COMPARISON_GUIDE.md", lambda: paper_guide(cfg)),
        ("WORK_LAPTOP_RUN_GUIDE.md", lambda: work_laptop_guide(cfg)),
    ):
        path = target_dir / filename
        write_text_atomically(path, builder())
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Section 23 final comparison
# ---------------------------------------------------------------------------

COMPARISON_COLUMNS: tuple[str, ...] = (
    "role",
    "source_demo",
    "case_or_trial",
    "wide_well_nm",
    "narrow_well_nm",
    "central_barrier_thickness_nm",
    "asymmetry_s",
    "grading_profile",
    "grading_thickness_nm",
    "relative_peak_chi2_abs",
    "peak_wavelength_nm",
    "relative_chi2_at_target_wavelength_abs",
    "signed_detuning_nm",
    "maximum_boundary_probability",
    "state_tracking_confidence",
    "robustness_score",
    "qc_status",
    "nextnano_evaluations_used",
    "validated",
    "note",
)

#: The six roles Section 23 requires the final comparison to cover.
COMPARISON_ROLES: tuple[tuple[str, str], ...] = (
    ("demo11_abrupt_reference", "Demo 11 abrupt reference"),
    ("demo12_best_grid_graded", "Best Demo 12 grid-search graded design"),
    ("demo13_best_target_wavelength", "Best valid Demo 13 target-wavelength BO design"),
    ("demo13_best_intrinsic_peak", "Best Demo 13 intrinsic-peak design"),
    ("demo13_most_robust", "Most robust Demo 13 design"),
    ("demo13_final_validated", "Final locally validated Demo 13 design"),
)


def comparison_rows(
    *,
    demo11: Mapping[str, Any] | None = None,
    demo12: Mapping[str, Any] | None = None,
    demo13_records: Sequence[Mapping[str, Any]] = (),
    evaluations_used: Mapping[str, Any] | None = None,
    validated_trial_index: int | None = None,
) -> list[dict[str, Any]]:
    """Build the Section 23 table, with every missing role stated explicitly."""

    evaluations = dict(evaluations_used or {})
    valid = [
        row
        for row in demo13_records
        if str(row.get("status")) == "completed" and row.get("trial_valid")
    ]

    def pick(metric: str, maximize: bool = True) -> Mapping[str, Any] | None:
        usable = [row for row in valid if row.get(metric) is not None]
        if not usable:
            return None
        return (max if maximize else min)(usable, key=lambda row: float(row[metric]))

    chosen: dict[str, Mapping[str, Any] | None] = {
        "demo11_abrupt_reference": demo11,
        "demo12_best_grid_graded": demo12,
        "demo13_best_target_wavelength": pick("relative_chi2_at_target_wavelength_abs"),
        "demo13_best_intrinsic_peak": pick("relative_peak_chi2_abs"),
        "demo13_most_robust": pick("robustness_score"),
        "demo13_final_validated": next(
            (
                row
                for row in valid
                if validated_trial_index is not None
                and int(row.get("trial_index", -1)) == int(validated_trial_index)
            ),
            None,
        ),
    }
    rows: list[dict[str, Any]] = []
    for key, label in COMPARISON_ROLES:
        record = chosen.get(key)
        if not record:
            rows.append(
                {
                    "role": label,
                    "source_demo": key.split("_")[0],
                    "case_or_trial": None,
                    **{column: None for column in COMPARISON_COLUMNS[3:-2]},
                    "validated": False,
                    "note": "not available in this bundle — no licensed result for this role",
                }
            )
            continue
        rows.append(
            {
                "role": label,
                "source_demo": str(record.get("source_demo", key.split("_")[0])),
                "case_or_trial": record.get("case_or_trial", record.get("trial_index")),
                "wide_well_nm": record.get("wide_well_nm", record.get("resolved_wide_well_nm")),
                "narrow_well_nm": record.get("narrow_well_nm", record.get("resolved_narrow_well_nm")),
                "central_barrier_thickness_nm": record.get(
                    "parameter_central_barrier_thickness_nm",
                    record.get("central_barrier_thickness_nm"),
                ),
                "asymmetry_s": record.get("parameter_asymmetry_s", record.get("asymmetry_s")),
                "grading_profile": record.get(
                    "parameter_grading_profile", record.get("grading_profile")
                ),
                "grading_thickness_nm": record.get(
                    "parameter_grading_thickness_nm", record.get("grading_thickness_nm")
                ),
                "relative_peak_chi2_abs": record.get("relative_peak_chi2_abs"),
                "peak_wavelength_nm": record.get("peak_wavelength_nm"),
                "relative_chi2_at_target_wavelength_abs": record.get("relative_chi2_at_target_wavelength_abs"),
                "signed_detuning_nm": record.get("signed_detuning_nm"),
                "maximum_boundary_probability": record.get("maximum_boundary_probability"),
                "state_tracking_confidence": record.get("state_tracking_confidence"),
                "robustness_score": record.get("robustness_score"),
                "qc_status": "valid" if record.get("trial_valid", True) else "invalid",
                "nextnano_evaluations_used": evaluations.get(key),
                "validated": bool(key == "demo13_final_validated" and record),
                "note": record.get("note", ""),
            }
        )
    return rows


def verdict(rows: Sequence[Mapping[str, Any]]) -> str:
    """State plainly what Ax did or did not find, per Section 23."""

    by_role = {str(row["role"]): row for row in rows}
    reference = by_role.get("Demo 11 abrupt reference")
    target = by_role.get("Best valid Demo 13 target-wavelength BO design")
    peak = by_role.get("Best Demo 13 intrinsic-peak design")
    validated = by_role.get("Final locally validated Demo 13 design")
    if reference is None or reference.get("relative_chi2_at_target_wavelength_abs") is None:
        return (
            "No verdict is possible: the Demo 11 abrupt reference has not been "
            "computed in this bundle, so there is nothing to compare against."
        )
    if target is None or target.get("relative_chi2_at_target_wavelength_abs") is None:
        return (
            "No verdict is possible: no valid Demo 13 design has been computed in "
            "this bundle."
        )
    statements: list[str] = []
    reference_target = float(reference["relative_chi2_at_target_wavelength_abs"])
    best_target = float(target["relative_chi2_at_target_wavelength_abs"])
    ratio = best_target / reference_target if reference_target else float("inf")
    statements.append(
        f"Stronger 1550 nm design: {'yes' if best_target > reference_target else 'no'} "
        f"({best_target:.4g} versus {reference_target:.4g}, ratio {ratio:.3g} on the "
        "relative arbitrary-unit scale)."
    )
    # A ratio of relative merits is not a measured enhancement factor. Saying so
    # once, here, keeps the headline number from being quoted as one.
    statements.append(
        "That ratio compares two Demo 11 Eq. 2 relative susceptibilities computed "
        "the same way; it is not a calibrated chi(2) ratio in pm/V and not an "
        "experimentally measured enhancement."
    )
    if peak and peak.get("relative_peak_chi2_abs") is not None and reference.get("relative_peak_chi2_abs") is not None:
        statements.append(
            "Stronger intrinsic design: "
            f"{'yes' if float(peak['relative_peak_chi2_abs']) > float(reference['relative_peak_chi2_abs']) else 'no'} "
            f"({float(peak['relative_peak_chi2_abs']):.4g} versus {float(reference['relative_peak_chi2_abs']):.4g})."
        )
    if target.get("signed_detuning_nm") is not None and reference.get("signed_detuning_nm") is not None:
        statements.append(
            "Better wavelength-matched design: "
            f"{'yes' if abs(float(target['signed_detuning_nm'])) < abs(float(reference['signed_detuning_nm'])) else 'no'} "
            f"(|detuning| {abs(float(target['signed_detuning_nm'])):.4g} nm versus "
            f"{abs(float(reference['signed_detuning_nm'])):.4g} nm)."
        )
    if validated and validated.get("relative_chi2_at_target_wavelength_abs") is not None:
        statements.append(
            "The improvement survived Stage 5 validation "
            f"(validated design χ² at target = "
            f"{float(validated['relative_chi2_at_target_wavelength_abs']):.4g})."
        )
    else:
        statements.append(
            "Stage 5 validation has not been completed, so this remains an apparent "
            "improvement that has not yet been shown to survive local refinement, "
            "mesh, state-count and padding checks."
        )
    return " ".join(statements)


def main() -> int:
    """Regenerate the repository's copies of the guides."""

    cfg = yaml.safe_load((DEMO_DIR / "demo.yaml").read_text(encoding="utf-8"))
    written = write_guides(DEMO_DIR, cfg, summary=None)
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
