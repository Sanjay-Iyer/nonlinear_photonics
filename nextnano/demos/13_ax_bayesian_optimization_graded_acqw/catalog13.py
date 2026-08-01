"""The one description of what Demo 13 produces, and what each thing means.

Guides that are written by hand go stale the moment a column is renamed, and
nobody notices because prose does not fail a test.  So the guides in ``guides/``
are **generated** from this module, and the entries here are checked against the
code that actually produces the artifacts:

* plot entries are checked against :data:`plots13.PLOT_SET` -- the list the
  renderer iterates -- and against :data:`report13.PLOT_GUIDE`;
* table entries are checked against :data:`tables13.TABLE_CATALOGUE`;
* metric entries are checked against :data:`tables13.COLUMN_UNITS`, so a unit
  can never be stated twice and differently;
* parameter entries are checked against real dotted paths in ``demo.yaml``, so a
  documented setting that no longer exists fails the suite.

That last point is what stops this being "a second hardcoded list": nothing here
is authoritative about units, filenames or configuration keys.  It carries only
the things code cannot know -- what a figure is *for*, what a reader should not
conclude from it, and how the v3 result in particular should be read.
"""

from __future__ import annotations

from typing import Any, Mapping

#: Populations a figure or table can be drawn from. Naming them once stops
#: "trials" meaning four different things across the guides.
POPULATIONS: Mapping[str, str] = {
    "completed": "the 16 trials that ran to completion (feasible or not)",
    "completed_valid": "only the 3 completed trials that satisfied every constraint",
    "all_proposals": "all 23 proposals, including the 7 refused before the solver",
    "rejected": "only the 7 proposals refused at preflight; none was simulated",
    "mbm_completed": "only the 10 completed model-based evaluations, numbered 1-10",
    "surrogate_grid": "predicted points on a grid, not evaluated designs",
    "genuine_graded": "only trials whose realized grade exceeded the resolvable minimum",
    "external": "reference results from Demo 11 or Demo 12, not Demo 13 trials",
}

#: Extra per-plot metadata the renderer cannot infer: which population is drawn,
#: and how the v3 campaign in particular should be read. Every filename in
#: `plots13.PLOT_SET` must appear here -- enforced by test.
PLOT_NOTES: Mapping[str, Mapping[str, str]] = {
    "bo_objective_value_by_trial.png": {
        "population": "completed",
        "v3": "16 points. Three sit above the feasibility line; the rest failed "
              "detuning. A high point is not a good design on its own.",
    },
    "bo_best_objective_so_far_by_iteration.png": {
        "population": "mbm_completed",
        "v3": "Uses MBM iterations 1-10, not proposal attempts. The curve only "
              "steps at a feasible trial, so it moves at t0017 and t0021.",
    },
    "bo_chi2_at_1550_by_trial.png": {
        "population": "completed",
        "v3": "The objective itself. t0021 is highest among feasible trials at "
              "0.411 relative units.",
    },
    "bo_peak_chi2_by_trial.png": {
        "population": "completed",
        "v3": "Intrinsic strength regardless of where the peak sits. t0021 "
              "reaches 0.577, higher than its 1550 nm value, because its peak "
              "is at 1537 nm.",
    },
    "bo_resonance_wavelength_by_trial.png": {
        "population": "completed",
        "v3": "Shows why most trials failed: the peak lands away from 1550 nm.",
    },
    "bo_detuning_from_1550_by_trial.png": {
        "population": "completed",
        "v3": "The binding constraint. t0021 is at -13 nm against a 15 nm "
              "bound; t0022 failed at -16 nm.",
    },
    "bo_asymmetry_vs_grading_thickness_objective.png": {
        "population": "completed",
        "v3": "Grading axis is the REALIZED thickness. The 11 abrupt trials sit "
              "on the 0 nm line; only 5 points are genuinely graded.",
    },
    "bo_barrier_thickness_vs_grading_thickness_objective.png": {
        "population": "completed",
        "v3": "Realized thickness again. Note the empty region below a 0.90 nm "
              "barrier: no grade fits there.",
    },
    "bo_asymmetry_vs_barrier_thickness_objective.png": {
        "population": "completed",
        "v3": "The clearest view of where the optimizer went: toward the thin "
              "barrier bound.",
    },
    "bo_grading_profile_objective_distribution.png": {
        "population": "completed",
        "v3": "CAUTION: erf 3, sigmoid 1, cosine 1, linear 0, and every graded "
              "trial was infeasible. This cannot rank profiles.",
    },
    "bo_parameter_sampling_by_iteration.png": {
        "population": "all_proposals",
        "v3": "Includes refused proposals so the search history is complete. "
              "Refused points built nothing.",
    },
    "bo_surrogate_mean_asymmetry_vs_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "Model belief, not measurement. 350 of 625 grid points are "
              "withheld because a grade there would be below 0.80 nm.",
    },
    "bo_surrogate_uncertainty_asymmetry_vs_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "Small error bars in the sampled region are not calibrated "
              "confidence: there are only 16 observations.",
    },
    "bo_acquisition_function_asymmetry_vs_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "Analytic EI on the objective ALONE. Its maximum can sit in "
              "infeasible territory. Read the constrained proxy in the CSV.",
    },
    "bo_surrogate_mean_barrier_vs_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "413 of 625 points are predictable; the rest cannot build a grade.",
    },
    "bo_surrogate_uncertainty_barrier_vs_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "Brightest away from the 16 evaluated designs, as expected.",
    },
    "bo_peak_chi2_vs_detuning_pareto.png": {
        "population": "completed",
        "v3": "The real tradeoff: the strongest designs are not the "
              "best-centred ones.",
    },
    "bo_chi2_1550_vs_peak_chi2.png": {
        "population": "completed",
        "v3": "Distance below the diagonal is detuning cost.",
    },
    "bo_chi2_1550_vs_boundary_probability.png": {
        "population": "completed",
        "v3": "Boundary probability is ~3e-5 everywhere, far inside its 1e-3 "
              "bound. This constraint never bound.",
    },
    "bo_chi2_1550_vs_state_tracking_confidence.png": {
        "population": "completed",
        "v3": "Confidence is high throughout. High confidence near the thin "
              "barrier still needs the Stage 5 anchor check.",
    },
    "bo_nonlinear_strength_vs_robustness_pareto.png": {
        "population": "completed_valid",
        "v3": "Empty until Stage 5 produces robustness scores.",
    },
    "bo_parameter_importance.png": {
        "population": "surrogate_grid",
        "v3": "Sensitivity of the FITTED MODEL, not of the physics. With 16 "
              "observations, negative indices are estimator noise.",
    },
    "bo_partial_dependence_asymmetry.png": {
        "population": "surrogate_grid",
        "v3": "A slice at fixed other coordinates, not a marginal average.",
    },
    "bo_partial_dependence_barrier_thickness.png": {
        "population": "surrogate_grid",
        "v3": "Rises toward the thin bound, which is why t0021 sits there.",
    },
    "bo_partial_dependence_grading_thickness.png": {
        "population": "surrogate_grid",
        "v3": "The x-axis is the PROPOSED FRACTION (dimensionless), not "
              "nanometres. Realized nm is a separate column in the CSV.",
    },
    "bo_grading_profile_effect.png": {
        "population": "genuine_graded",
        "v3": "5 trials total across 3 profiles. Observations, never a ranking.",
    },
    "bo_valid_and_invalid_trials_by_iteration.png": {
        "population": "completed",
        "v3": "13 of 16 invalid. That is the headline result of v3.",
    },
    "bo_failure_reason_counts.png": {
        "population": "all_proposals",
        "v3": "Two distinct groups: 7 refused before the solver, 13 completed "
              "but infeasible. They are not the same failure.",
    },
    "bo_boundary_probability_by_trial.png": {
        "population": "completed",
        "v3": "Nearly constant, which is why this constraint carries no "
              "information for the surrogate.",
    },
    "bo_state_tracking_confidence_by_trial.png": {
        "population": "completed",
        "v3": "All above the 0.8 threshold.",
    },
    "bo_validity_map_asymmetry_vs_grading_thickness.png": {
        "population": "completed",
        "v3": "Where feasible designs live: a narrow sliver, only 3 points.",
    },
    "baseline_and_top_bo_designs_chi2_spectra.png": {
        "population": "external",
        "v3": "Needs raw spectra; absent from the transferred bundle.",
    },
    "baseline_and_best_bo_composition_profiles.png": {
        "population": "external",
        "v3": "Needs alloy-composition output, which was NOT transferred. This "
              "is the figure that would verify realized grading.",
    },
    "baseline_and_best_bo_conduction_band_edges.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "baseline_and_best_bo_valence_band_edges.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "baseline_and_best_bo_electron_wavefunctions.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "baseline_and_best_bo_hole_wavefunctions.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "baseline_and_best_bo_state_localization.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "baseline_and_best_bo_transition_energies.png": {
        "population": "external", "v3": "Needs raw solver output; not in the bundle."},
    "top_bo_designs_chi2_spectra.png": {
        "population": "completed_valid", "v3": "Needs raw spectra; not in the bundle."},
    "bo_vs_random_search_best_objective.png": {
        "population": "completed",
        "v3": "Only meaningful after a Demo 12 replay; not run for v3.",
    },
    "bo_vs_grid_search_best_objective.png": {
        "population": "completed", "v3": "As above."},
    "bo_random_grid_evaluations_to_best_known_result.png": {
        "population": "completed", "v3": "As above."},
    "demo11_demo12_demo13_best_chi2_spectra.png": {
        "population": "external",
        "v3": "Cross-demo comparison. v2 and v3 numbers are NOT comparable: "
              "different mesh and different search space.",
    },
    "paper_figure2d_simulation_comparison_full_range.png": {
        "population": "external",
        "v3": "Normalized shape comparison only. Never a calibration.",
    },
    "paper_figure2d_simulation_comparison_telecom_range.png": {
        "population": "external", "v3": "As above, zoomed to the telecom band."},
    "paper_measured_sh_intensity_comparison.png": {
        "population": "external",
        "v3": "Digitized from a figure. Visual reference only, never a target.",
    },
}

#: What each important result column means. Units are NOT stated here -- they
#: come from `tables13.COLUMN_UNITS`, so they cannot disagree.
METRIC_NOTES: Mapping[str, Mapping[str, str]] = {
    "relative_chi2_at_target_wavelength_abs": {
        "plain": "How strong the second-order response is exactly at 1550 nm.",
        "direction": "higher is better",
        "definition": "|chi(2)| from Demo 11 Eq. 2 evaluated at the target wavelength.",
        "caution": "A RELATIVE arbitrary-unit merit. Never pm/V. Only comparable "
                   "between designs computed with the same mesh and settings.",
    },
    "relative_peak_chi2_abs": {
        "plain": "The strongest response anywhere in the scanned band.",
        "direction": "higher is better",
        "definition": "Maximum |chi(2)| over the focused wavelength window.",
        "caution": "A high peak at the wrong wavelength does not help a 1550 nm device.",
    },
    "peak_wavelength_nm": {
        "plain": "Where the response peaks.",
        "direction": "closer to 1550 nm is better",
        "definition": "Wavelength of the maximum of |chi(2)|.",
        "caution": "Shifts strongly with well asymmetry and barrier thickness.",
    },
    "signed_detuning_nm": {
        "plain": "How far the peak sits from 1550 nm, with direction.",
        "direction": "closer to zero is better",
        "definition": "peak_wavelength_nm - 1550.",
        "caution": "REPORTED but never constrained. The sign tells you which way "
                   "to move; the constraint uses the absolute value.",
    },
    "absolute_detuning_nm": {
        "plain": "How far the peak sits from 1550 nm, ignoring direction.",
        "direction": "lower is better",
        "definition": "|peak_wavelength_nm - 1550|.",
        "caution": "THIS is the constrained quantity, bounded at 15 nm. It is what "
                   "made 13 of 16 v3 trials infeasible.",
    },
    "trial_valid": {
        "plain": "Did this trial satisfy every constraint and QC check?",
        "direction": "True is required",
        "definition": "All outcome constraints satisfied and all QC checks passed.",
        "caution": "An invalid trial keeps its metrics; it is a result, not a gap.",
    },
    "orthonormality_error": {
        "plain": "How far the computed states are from being mutually orthonormal.",
        "direction": "lower is better",
        "definition": "Max deviation of the state overlap matrix from the identity.",
        "caution": "~3e-7 throughout, four orders inside its 1e-3 bound, so it is "
                   "deliberately NOT modelled by Ax.",
    },
    "origin_independence_valid": {
        "plain": "Does the answer stay the same if the coordinate origin moves?",
        "direction": "1 is required",
        "definition": "chi(2) recomputed after a 100 nm origin shift must agree.",
        "caution": "A binary flag. Enforced outside Ax; a Gaussian model cannot "
                   "usefully represent a 0/1 outcome.",
    },
    "maximum_boundary_probability": {
        "plain": "The largest fraction of any single state leaking to the domain edge.",
        "direction": "lower is better",
        "definition": "Max over states of the probability inside the outer 5% of the domain.",
        "caution": "Distinct from total_boundary_probability, which sums over states. "
                   "~3e-5 in v3, so this constraint never bound.",
    },
    "state_tracking_confidence": {
        "plain": "How sure the code is that it followed the same physical state.",
        "direction": "higher is better",
        "definition": "Overlap of this trial's states with the reference trial's.",
        "caution": "Self-consistency, not proof. Least discriminating exactly where "
                   "the barrier is thinnest and the states are near-degenerate.",
    },
    "state_tracking_margin": {
        "plain": "How much better the chosen assignment was than the runner-up.",
        "direction": "higher is better",
        "definition": "Difference between the best and second-best overlap.",
        "caution": "A small margin with high confidence still means an ambiguous match.",
    },
    "proposed_grading_fraction": {
        "plain": "What fraction of the available room the optimizer asked to grade.",
        "direction": "neither",
        "definition": "The Ax coordinate, dimensionless, in [0.35, 1.0].",
        "caution": "NOT a length. Multiply by maximum_feasible_grading_nm to get "
                   "nanometres, then apply mesh snapping.",
    },
    "realized_grading_thickness_nm": {
        "plain": "The grade width actually built in the deck.",
        "direction": "neither",
        "definition": "Mesh-snapped width; 0 for an abrupt design.",
        "caution": "The ONLY width any physical statement may use.",
    },
    "maximum_feasible_grading_nm": {
        "plain": "The widest grade this design's geometry could build.",
        "direction": "neither",
        "definition": "central barrier thickness - minimum_flat_region_nm.",
        "caution": "Below a 0.90 nm barrier this falls under 0.80 nm and no grade fits.",
    },
    "probability_of_feasibility": {
        "plain": "Model's estimate that a point satisfies every modelled constraint.",
        "direction": "higher is better",
        "definition": "Product of per-constraint Gaussian tail probabilities.",
        "caution": "Assumes the constraints are independent; Ax does not. A proxy.",
    },
    "constrained_expected_improvement_proxy": {
        "plain": "Expected improvement weighted by the chance of being feasible.",
        "direction": "higher is better",
        "definition": "expected_improvement x probability_of_feasibility.",
        "caution": "NOT Ax's acquisition. Ax used a Monte-Carlo constrained "
                   "acquisition that cannot be replayed from a snapshot.",
    },
    "expected_acquisition_value": {
        "plain": "What Ax's own acquisition scored this proposal at, historically.",
        "direction": "higher is better",
        "definition": "Recorded on the generator run at proposal time.",
        "caution": "Empty for Sobol trials, which are quasi-random.",
    },
    "best_objective_so_far": {
        "plain": "The best FEASIBLE objective seen up to this iteration.",
        "direction": "higher is better",
        "definition": "Running maximum over valid completed trials.",
        "caution": "An invalid trial never improves it, however high its objective.",
    },
    "rejection_reason": {
        "plain": "Why a proposal was refused before the solver ran.",
        "direction": "neither",
        "definition": "Category plus detail; all 7 v3 refusals were subresolution_grade.",
        "caution": "A refusal is not a duplicate and not a solver failure.",
    },
    "mbm_iteration_number": {
        "plain": "Which model-based BO iteration this completed evaluation was.",
        "direction": "neither",
        "definition": "1..10 over completed model-based trials, in trial order.",
        "caution": "The ledger's `iteration` column counts proposal ATTEMPTS and "
                   "reached 17 in this 10-iteration study. Do not plot it as the "
                   "BO iteration.",
    },
}

#: User-adjustable settings. `path` must be a real dotted path in demo.yaml --
#: enforced by test, so a documented setting that no longer exists fails.
PARAMETER_NOTES: tuple[Mapping[str, Any], ...] = (
    {"path": "bo.search_space.asymmetry_s", "kind": "BO parameter",
     "plain": "How unequal the two wells are. 0.5 would be symmetric; lower means "
              "a wider left well.",
     "units": "dimensionless", "invalidates_checkpoint": True,
     "increase": "shifts the resonance and changes which states overlap",
     "decrease": "same axis, opposite direction; very low values give a near-zero response",
     "interacts": "sets the peak wavelength together with the barrier, so it "
                  "drives the detuning constraint"},
    {"path": "bo.search_space.central_barrier_thickness_nm", "kind": "BO parameter",
     "plain": "Thickness of the AlGaAs barrier between the two wells.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "weakens tunnel coupling; states localize in one well",
     "decrease": "strengthens coupling and generally raises the response, which is "
                 "why the optimizer pushes to the lower bound",
     "interacts": "CAPS the grading: max grade = barrier - minimum_flat_region_nm. "
                  "Abrupt designs may use 0.85 nm, but a genuine 0.80 nm grade "
                  "needs a barrier of at least 0.90 nm"},
    {"path": "bo.search_space.encoding", "kind": "BO parameter",
     "plain": "How the abrupt/graded choice is expressed to Ax. 'hierarchical' "
              "gives abrupt designs no grading parameters at all.",
     "units": "category", "invalidates_checkpoint": True,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "hierarchical prevents one abrupt structure being proposed under "
                  "five different profile labels"},
    {"path": "bo.search_space.grading_profile", "kind": "BO parameter",
     "plain": "Shape of the composition ramp across a graded interface.",
     "units": "category", "invalidates_checkpoint": True,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "only 'linear' renders natively; the rest use a 16-sublayer "
                  "staircase, which is why the grade mesh must be fine"},
    {"path": "bo.search_space.grading_fraction_of_feasible_max", "kind": "BO parameter",
     "plain": "What fraction of the available room to grade. Dimensionless, not nm.",
     "units": "dimensionless", "invalidates_checkpoint": True,
     "increase": "wider realized grade", "decrease": "narrower, and below the "
                 "resolvable minimum the proposal is refused",
     "interacts": "the realized width is this times maximum_feasible_grading_nm, "
                  "then snapped to the mesh"},
    {"path": "bo.search_space.minimum_mesh_resolvable_nonzero_grading_nm",
     "kind": "geometry gate",
     "plain": "The narrowest grade this mesh and profile implementation can build.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "more graded proposals refused", "decrease": "risks accepting a "
                 "grade the grid cannot represent",
     "interacts": "derived from the mesh and staircase_sublayers; must not sit "
                  "below minimum_graded_thickness_nm"},
    {"path": "bo.search_space.minimum_graded_thickness_nm", "kind": "geometry gate",
     "plain": "At or below this width a design is treated as abrupt.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "more designs collapse to abrupt", "decrease": "risks calling a "
                 "sub-mesh step a graded interface",
     "interacts": "must be at least the resolvable minimum; validated at startup"},
    {"path": "bo.search_space.reject_subresolution_grades", "kind": "geometry gate",
     "plain": "Refuse a too-narrow graded proposal instead of silently making it abrupt.",
     "units": "boolean", "invalidates_checkpoint": False,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "with it off, a 'sigmoid' trial with no grade enters the "
                  "surrogate's training data -- the v2 defect"},
    {"path": "bo.search_space.grading_fraction_spans_feasible_interval",
     "kind": "BO parameter",
     "plain": "Map the fraction onto [minimum, maximum] instead of [0, maximum], so "
              "every value builds a resolvable grade.",
     "units": "boolean", "invalidates_checkpoint": True,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "changes what a stored fraction MEANS, so it is part of the "
                  "experiment schema; v3 ran with it false"},
    {"path": "numerical.active_region_grid_spacing_nm", "kind": "fixed simulation setting",
     "plain": "Mesh spacing through the wells and barriers.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "faster, less resolved", "decrease": "slower, better resolved; "
                 "v3 uses 0.05 nm so a 0.85 nm barrier spans 17 cells",
     "interacts": "two campaigns at different meshes are NOT comparable and cannot "
                  "warm-start each other"},
    {"path": "grading.minimum_grid_points_per_grade", "kind": "fixed simulation setting",
     "plain": "How finely the mesh is refined INSIDE a graded region.",
     "units": "count", "invalidates_checkpoint": False,
     "increase": "better-resolved ramp, slightly slower",
     "decrease": "risks a staircase finer than the grid that samples it",
     "interacts": "must give at least one grid spacing per staircase sublayer; "
                  "v3 uses 32 points so each of 16 sublayers is sampled twice"},
    {"path": "grading.minimum_flat_region_nm", "kind": "geometry gate",
     "plain": "Flat material each layer keeps outside a centred grade.",
     "units": "nm", "invalidates_checkpoint": False,
     "increase": "less room to grade", "decrease": "more room, but thinner flat regions",
     "interacts": "sets max feasible grade = central barrier - this value"},
    {"path": "bo.target_wavelength_nm", "kind": "fixed simulation setting",
     "plain": "The wavelength the design is being optimized for.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "moves the target", "decrease": "moves the target",
     "interacts": "detuning is measured from this"},
    {"path": "bo.outcome_constraints.maximum_detuning_nm", "kind": "QC threshold",
     "plain": "How far the peak may sit from the target and still count as feasible.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "more trials feasible", "decrease": "fewer",
     "interacts": "THE binding constraint in v3: 13 of 16 trials failed on it"},
    {"path": "bo.outcome_constraints.maximum_boundary_probability", "kind": "QC threshold",
     "plain": "How much of a state may leak to the simulation edge.",
     "units": "probability", "invalidates_checkpoint": True,
     "increase": "accepts less-confined states", "decrease": "stricter confinement",
     "interacts": "nearly constant in v3, so it carries no information for the model"},
    {"path": "bo.outcome_constraints.minimum_state_tracking_confidence",
     "kind": "QC threshold",
     "plain": "How confident the state matching must be.",
     "units": "overlap in [0,1]", "invalidates_checkpoint": True,
     "increase": "stricter", "decrease": "risks comparing different physical states",
     "interacts": "most fragile at the thinnest barrier"},
    {"path": "numerical.number_of_electron_states", "kind": "fixed simulation setting",
     "plain": "How many electron states the solver is asked for.",
     "units": "count", "invalidates_checkpoint": True,
     "increase": "safer sum, slower", "decrease": "risks truncating the chi(2) sum",
     "interacts": "Demo 11's window convergence is on record as FAILED, so this "
                  "must be checked in Stage 5"},
    {"path": "numerical.domain_padding_nm", "kind": "fixed simulation setting",
     "plain": "Extra material outside the active region.",
     "units": "nm", "invalidates_checkpoint": True,
     "increase": "less edge leakage, slower", "decrease": "risks boundary artifacts",
     "interacts": "tested against boundary probability in Stage 5"},
    {"path": "bo.num_initial_trials", "kind": "workflow setting",
     "plain": "How many quasi-random Sobol designs to run before modelling.",
     "units": "count", "invalidates_checkpoint": False,
     "increase": "better coverage, more solver time",
     "decrease": "the model starts from too little data",
     "interacts": "v3 proposed 7 and completed 6; one was refused"},
    {"path": "bo.num_iterations", "kind": "workflow setting",
     "plain": "How many model-guided evaluations to run after initialization.",
     "units": "count", "invalidates_checkpoint": False,
     "increase": "more refinement, more solver time", "decrease": "may stop early",
     "interacts": "one iteration = one COMPLETED model-based evaluation; a refused "
                  "proposal does not consume one"},
    {"path": "bo.batch_size", "kind": "workflow setting",
     "plain": "How many designs to propose at once.",
     "units": "count", "invalidates_checkpoint": False,
     "increase": "parallel evaluation, less sequential learning", "decrease": "n/a",
     "interacts": "v3 used 1, so every proposal saw all previous results"},
    {"path": "bo.random_seed", "kind": "workflow setting",
     "plain": "Makes the Sobol sequence reproducible.",
     "units": "integer", "invalidates_checkpoint": False,
     "increase": "different sequence", "decrease": "different sequence",
     "interacts": "does not make GP fitting bitwise reproducible across versions"},
    {"path": "workflow.mode", "kind": "workflow setting",
     "plain": "What the run does: analyse existing results, or spend solver time.",
     "units": "category", "invalidates_checkpoint": False,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "analyze_existing_results opens the experiment READ-ONLY and "
                  "calls no solver; closed_loop SPENDS LICENSED SOLVER TIME"},
    {"path": "workflow.experiment_state_dir", "kind": "workflow setting",
     "plain": "Which experiment the run reads and writes.",
     "units": "path", "invalidates_checkpoint": False,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "analysis mode refuses to CREATE a missing directory and lists "
                  "the ones that exist instead"},
    {"path": "simulation.run_solver", "kind": "workflow setting",
     "plain": "Whether the licensed solver may be called at all.",
     "units": "boolean", "invalidates_checkpoint": False,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "can only ever DISABLE the solver; a machine without a licence "
                  "still skips execution when this is true"},
    {"path": "validation_study.enabled", "kind": "Stage 5 setting",
     "plain": "Whether Stage 5 validation cases are generated.",
     "units": "boolean", "invalidates_checkpoint": False,
     "increase": "n/a", "decrease": "n/a",
     "interacts": "Stage 5 must write to its own directory, never the protected "
                  "v3 experiment"},
    {"path": "validation_study.mesh_convergence_nm", "kind": "Stage 5 setting",
     "plain": "Which mesh spacings to re-run a top design at.",
     "units": "nm", "invalidates_checkpoint": False,
     "increase": "coarser check", "decrease": "finer, slower",
     "interacts": "this is the Stage 5 gate: everything else is conditional on it"},
)


def plot_population(filename: str) -> str:
    """The trial population a figure draws from, spelled out."""

    note = PLOT_NOTES.get(filename, {})
    return POPULATIONS.get(str(note.get("population", "")), "unspecified")


def plot_csv_name(filename: str) -> str:
    """The CSV a figure is drawn from. Derived, never stated separately."""

    return f"plot_data/{filename.rsplit('.', 1)[0]}.csv"
