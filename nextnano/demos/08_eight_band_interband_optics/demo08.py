"""Demo 8 — interband optical transitions from an 8-band k.p model.

A transition being energetically available says nothing about whether it is
optically allowed.  Strength lives in the matrix element, and the matrix element
depends on the polarisation and on how well the electron and hole envelopes
overlap.  This demo computes both and refuses to call a transition strong on
energy alone.

MEASURED AT HOME, and the reason the demo needs 8 bands: asking nextnano++ for
``momentum_matrix_elements`` over *separate* one-band Gamma and HH solutions
produces only ``Gamma_Gamma/`` and ``HH_HH/`` -- intraband elements within each
band.  No interband element exists, because the two solutions live in different
eigenproblems.  Only the coupled 8-band Hamiltonian puts conduction and valence
states in the same problem, which is where an interband momentum matrix element
can come from at all.

Licensed testing established that ``quantum{momentum_matrix_elements{KP8{}}}``
writes the *envelope* momentum operator in hbar/nm. For a 1D structure its
in-plane component is identically zero, so it is not the interband optical
response. The actual absorption spectrum must come from
``optics{quantum_spectra{}}``, which includes the Bloch/Kane contribution and
reports an absorption coefficient in cm^-1. The envelope-momentum tables are
retained only as diagnostics.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import layers
import outputs
import plots as plotting
import quantum1d
import sweeps
from demo_workflow import DemoError, write_csv, write_json_atomically

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("model_comparison_transitions.png", "One-band vs 6-band vs 8-band transitions"),
    ("state_composition.png", "State composition of the 8-band states"),
    ("electron_hole_overlap.png", "Electron–hole wavefunction overlap"),
    ("matrix_element_heatmap.png", "Transition matrix-element map"),
    ("polarization_resolved_strengths.png", "Polarisation-resolved strengths"),
    ("spectrum.png", "Solver interband absorption spectrum"),
    ("spectrum_symmetry_broken.png", "Symmetric versus symmetry-broken spectrum"),
    ("absorption_vs_field.png", "Peak solver absorption versus field"),
    ("k_convergence.png", "Spectral convergence with in-plane k sampling"),
    ("spectral_resolution_check.png", "Spectrum under two spectral resolutions"),
)

UNVALIDATED_SYNTAX: tuple[str, ...] = (
    "optics{ quantum_spectra{} } absorption output file location in nextnano++ 3.0.0",
)

SPECTRUM_UNITS = "arbitrary (relative lineshape; NOT an absorption coefficient)"


def build_stack(cfg: Mapping[str, Any], *, symmetry_broken: bool = False) -> layers.LayerStack:
    """GaAs / InGaAs well / GaAs, optionally with a higher-indium step."""

    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    active = float(numerical["active_region_grid_spacing_nm"])
    exterior = float(numerical["exterior_grid_spacing_nm"])
    if not symmetry_broken:
        return layers.strained_single_well(
            well_width_nm=float(scientific["well_width_nm"]),
            barrier_width_nm=float(scientific["barrier_width_nm"]),
            indium_fraction=float(scientific["indium_fraction"]),
            active_grid_spacing_nm=active,
            exterior_grid_spacing_nm=exterior,
        )
    step = float(scientific["symmetry_breaking_step_nm"])
    main_width = float(scientific["well_width_nm"]) - step
    if main_width <= 0:
        raise DemoError(
            "symmetry_breaking_step_nm must be smaller than well_width_nm."
        )
    return layers.build_stack(
        [
            layers.Layer(
                "left_outer_barrier",
                layers.GAAS,
                float(scientific["barrier_width_nm"]),
                None,
                exterior,
            ),
            layers.Layer(
                "well_step",
                layers.INGAAS,
                step,
                float(scientific["symmetry_breaking_indium_fraction"]),
                active,
            ),
            layers.Layer(
                "well",
                layers.INGAAS,
                main_width,
                float(scientific["indium_fraction"]),
                active,
            ),
            layers.Layer(
                "right_outer_barrier",
                layers.GAAS,
                float(scientific["barrier_width_nm"]),
                None,
                exterior,
            ),
        ],
        exterior_grid_spacing_nm=exterior,
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "qw"))


def active_model(cfg: Mapping[str, Any]) -> dict[str, Any]:
    models = cfg.get("models") or []
    if not models:
        raise DemoError("demo.yaml must declare at least one model stage.")
    return dict(models[0])


def polarizations(cfg: Mapping[str, Any]) -> dict[str, str]:
    declared = (cfg.get("analysis") or {}).get("polarizations") or {}
    if not declared:
        raise DemoError("analysis.polarizations must name at least one polarization.")
    return {str(name): str(vector) for name, vector in declared.items()}


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    model = active_model(cfg)
    symmetry_broken = bool(model.get("symmetry_broken"))
    stack = build_stack(cfg, symmetry_broken=symmetry_broken)
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    electrons = int(numerical["number_of_electron_states"])
    holes = int(numerical["number_of_hole_states"])
    band_model = str(model.get("band_model", "kp8"))
    k_parallel = bool(model.get("k_parallel"))
    k_block = (
        "            k_integration{\n"
        f"                num_points    = {int(numerical['k_parallel_num_points'])}\n"
        f"                relative_size = {float(numerical['k_parallel_relative_size']):.6g}\n"
        "            }\n"
        if k_parallel
        else "            k_integration_disabled{}\n"
    )

    if band_model == "one_band":
        model_block = (
            f"        Gamma{{ num_ev = {electrons} }}\n"
            f"        HH{{    num_ev = {holes} }}\n"
            f"        LH{{    num_ev = {holes} }}\n"
        )
        spinor_output = ""
    elif band_model == "kp6":
        model_block = (
            f"        Gamma{{ num_ev = {electrons} }}\n"
            "        kp_6band{\n"
            f"            num_ev = {holes}\n"
            f"{k_block}"
            "        }\n"
        )
        spinor_output = "            spinor_composition = yes\n"
    elif band_model == "kp8":
        model_block = (
            "        kp_8band{\n"
            f"            num_electrons = {electrons}\n"
            f"            num_holes     = {holes}\n"
            f"{k_block}"
            "            classify_by_energy{}\n"
            "        }\n"
        )
        spinor_output = "            spinor_composition = yes\n"
    else:
        raise DemoError(f"unsupported band_model {band_model!r}.")

    optics = str(model.get("optics", "overlaps"))
    lines: list[str] = []
    if band_model == "one_band":
        lines.append("        transition_energies{ Gamma_HH{}  Gamma_LH{} }")
        lines.append("        overlap_integrals{ Gamma_HH{}  Gamma_LH{} }")
    elif band_model == "kp6":
        lines.append("        transition_energies{ Gamma_KP6{} }")
        lines.append("        overlap_integrals{ Gamma_KP6{} }")
    else:
        lines.append("        transition_energies{ KP8{} }")
    if optics == "matrix_elements":
        polarization_lines = "\n".join(
            f"            polarization{{ name = \"{name}\"  re = {vector} }}"
            for name, vector in polarizations(cfg).items()
        )
        band_tag = {"one_band": "Gamma{}\n            HH{}", "kp6": "KP6{}", "kp8": "KP8{}"}[
            band_model
        ]
        lines.append(
            "        momentum_matrix_elements{\n"
            f"{polarization_lines}\n"
            f"            {band_tag}\n"
            "            output_matrix_elements      = yes\n"
            "            output_oscillator_strengths = yes\n"
            "        }"
        )
    optical_block = "\n".join(lines) + "\n" if lines else ""

    # The quantum-region matrix-element request above is diagnostic. For kp8,
    # the physical interband response is computed by the dedicated optical
    # solver, which includes the Bloch/Kane contribution.
    if band_model == "kp8" and optics == "matrix_elements":
        polarization_lines = "\n".join(
            f'        polarization{{ name = "{name}"  re = {vector} }}'
            for name, vector in polarizations(cfg).items()
        )
        energy_min = float(numerical["spectral_energy_min_eV"])
        energy_max = float(numerical["spectral_energy_max_eV"])
        spectral_points = int(numerical["spectral_points"])
        energy_resolution = (energy_max - energy_min) / (spectral_points - 1)
        broadening_eV = float(numerical["broadening_meV"]) / 1000.0
        quantum_spectra_block = (
            "\noptics{\n"
            "    quantum_spectra{\n"
            f'        name = "{region_name(cfg)}"\n'
            "        interband = yes\n"
            "        intraband = no\n"
            "        enable_hole_hole = no\n"
            "        enable_electron_hole = yes\n"
            "        enable_electron_electron = no\n"
            "        occupation_ignore = yes\n"
            "        classify_states = yes\n"
            "        k_integration{\n"
            f"            num_points = {int(numerical['k_parallel_num_points'])}\n"
            f"            relative_size = {float(numerical['k_parallel_relative_size']):.9g}\n"
            "        }\n"
            f"{polarization_lines}\n"
            f"        min_energy = {energy_min:.9g}\n"
            f"        max_energy = {energy_max:.9g}\n"
            f"        energy_resolution = {energy_resolution:.9g}\n"
            f"        energy_broadening_lorentzian = {broadening_eV:.9g}\n"
            "        absorption = yes\n"
            "        spontaneous_emission = no\n"
            "        output_energies = yes\n"
            "        output_transitions = yes\n"
            "        output_spinor_components = yes\n"
            "        output_spectra{\n"
            "            im_epsilon = yes\n"
            "            absorption_coeff = yes\n"
            "            spectra_over_energy = yes\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        run_optics_block = "    optics{}\n"
    else:
        quantum_spectra_block = ""
        run_optics_block = ""

    field_kV_cm = float(scientific["electric_field_kV_cm"])
    if abs(field_kV_cm) > 0:
        poisson_block = (
            "\npoisson{\n"
            "    electric_field{\n"
            "        direction = [1, 0, 0]\n"
            f"        strength  = {quantum1d.kv_per_cm_to_volts_per_metre(field_kV_cm):.9g}"
            f"   # V/m; {field_kV_cm:.9g} kV/cm\n"
            "    }\n"
            "    output_potential{}\n"
            "    output_electric_field{}\n"
            "}\n"
        )
    else:
        poisson_block = "\n# Zero applied field: no poisson{} block.\n"

    return {
        "temperature_K": scientific["temperature_K"],
        "substrate_material": str(scientific["substrate_material"]),
        "growth_direction_vector": str(scientific["growth_direction"]),
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(contact_name="qw_contact"),
        "quantum_region_name": region_name(cfg),
        "quantum_start_nm": f"{start:.9g}",
        "quantum_end_nm": f"{end:.9g}",
        "model_block": model_block,
        "spinor_output": spinor_output.rstrip("\n"),
        "optical_block": optical_block,
        "output_state_count": max(electrons, holes),
        "poisson_block": poisson_block,
        "quantum_spectra_block": quantum_spectra_block,
        "run_optics_block": run_optics_block,
    }


# ---------------------------------------------------------------------------
# post-processed spectrum
# ---------------------------------------------------------------------------


def lorentzian_spectrum(
    energies_eV: Sequence[float],
    strengths: Sequence[float],
    *,
    minimum_eV: float,
    maximum_eV: float,
    points: int,
    broadening_meV: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Sum of Lorentzians, one per transition, in arbitrary relative units.

    ``broadening_meV`` is the full width at half maximum of each line. It stands
    in for every homogeneous and inhomogeneous broadening mechanism the
    calculation does not contain -- dephasing, phonons, interface roughness,
    well-width fluctuation -- lumped into a single phenomenological number. It is
    an input, not a result.
    """

    if points < 2:
        raise DemoError("spectral_points must be at least 2.")
    if maximum_eV <= minimum_eV:
        raise DemoError("spectral_energy_max_eV must exceed spectral_energy_min_eV.")
    if broadening_meV <= 0:
        raise DemoError("broadening_meV must be positive.")
    grid = np.linspace(float(minimum_eV), float(maximum_eV), int(points))
    gamma = 0.5 * float(broadening_meV) / 1000.0
    spectrum = np.zeros_like(grid)
    for energy, strength in zip(energies_eV, strengths):
        if not (math.isfinite(float(energy)) and math.isfinite(float(strength))):
            continue
        spectrum += float(strength) * (gamma**2) / (
            (grid - float(energy)) ** 2 + gamma**2
        )
    return grid, spectrum


def _matrix_table(
    profile: outputs.ParserProfile,
    raw: Path,
    region: str,
    key: str,
    polarization: str | None = None,
) -> dict[tuple[int, int], dict[str, float]] | None:
    substitutions = {"region": region}
    if polarization is not None:
        substitutions["polarization"] = polarization
    resolved = outputs.resolve_outputs(profile, raw, [key], substitutions=substitutions)
    paths = resolved.many(key)
    if not paths:
        return None
    return outputs.read_matrix_elements(paths[0])


def _spinor_composition(
    profile: outputs.ParserProfile,
    raw: Path,
    region: str,
    *,
    dominant_threshold: float,
) -> list[dict[str, Any]]:
    resolved = outputs.resolve_outputs(
        profile, raw, ["spinor_composition_kp8"], substitutions={"region": region}
    )
    paths = resolved.many("spinor_composition_kp8")
    if not paths:
        return []
    table = outputs.read_table(paths[0])
    names = [name for name, _ in table.header][1:] or [
        f"component_{index}" for index in range(table.n_columns - 1)
    ]
    rows: list[dict[str, Any]] = []
    for index, values in enumerate(table.data, start=1):
        weights = {
            names[column]: float(values[column + 1])
            for column in range(min(len(names), table.n_columns - 1))
        }
        normalised = analysis.normalise_weights(weights)
        character, fraction = analysis.classify_character(
            normalised, dominant_threshold=dominant_threshold
        )
        rows.append(
            {
                "state": index,
                "character": character,
                "dominant_fraction": fraction,
                **normalised,
            }
        )
    return rows


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    model = active_model(cfg)
    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    numerical = cfg["numerical"]
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    region = region_name(cfg)
    band_model = str(model.get("band_model", "kp8"))

    observables: dict[str, Any] = {
        "model": model.get("name"),
        "band_model": band_model,
        "k_parallel_enabled": bool(model.get("k_parallel")),
        "symmetry_broken": bool(model.get("symmetry_broken")),
        "well_width_nm": float(cfg["scientific"]["well_width_nm"]),
        "electric_field_kV_cm": float(cfg["scientific"]["electric_field_kV_cm"]),
        "broadening_meV": float(numerical["broadening_meV"]),
        "spectral_points": int(numerical["spectral_points"]),
        "k_parallel_num_points": int(numerical["k_parallel_num_points"]),
        "polarization_convention": {
            name: vector for name, vector in polarizations(cfg).items()
        },
    }
    validation: dict[str, Any] = {}

    band_path = outputs.resolve_outputs(profile, raw, ["bandedges"]).one("bandedges")
    band = outputs.read_table(band_path).select(dict(cfg["outputs"]["bandedge_columns"]))
    write_csv(extracted / "band_edges.csv", band)
    compositions = (
        _spinor_composition(
            profile,
            raw,
            region,
            dominant_threshold=float(
                analysis_cfg.get("character_dominant_threshold", 0.60)
            ),
        )
        if band_model == "kp8"
        else []
    )
    if compositions:
        write_json_atomically(extracted / "state_composition.json", compositions)
        observables["state_composition"] = compositions
        validation["state_composition_normalised"] = all(
            abs(
                sum(
                    float(value)
                    for key, value in row.items()
                    if key not in {"state", "character", "dominant_fraction"}
                )
                - 1.0
            )
            <= 1e-6
            for row in compositions
        )
    if band_model == "kp8":
        validation["state_composition_present"] = bool(compositions)
        observables["state_composition_count"] = len(compositions)

    # --- transition energies --------------------------------------------------
    transition_key = {
        "one_band": "transition_energies_gamma_hh",
        "kp6": "transition_energies_gamma_kp6",
        "kp8": "transition_energies_kp8",
    }[band_model]
    resolved = outputs.resolve_outputs(
        profile, raw, [transition_key], substitutions={"region": region}
    )
    transition_paths = resolved.many(transition_key)
    transitions = (
        outputs.read_matrix_elements(transition_paths[0])
        if transition_paths
        else None
    )
    if transitions is None:
        outputs.require_or_diagnose(
            resolved, raw, [transition_key], why="transition_energies{} was requested"
        )
    assert transitions is not None
    energy_column = outputs.value_column_with_unit(transition_paths[0], unit="eV")
    if band_model == "kp8":
        spectrum_resolved = outputs.resolve_outputs(
            profile,
            raw,
            ["energy_spectrum_kp8"],
            substitutions={"region": region},
        )
        spectrum_path = spectrum_resolved.one("energy_spectrum_kp8")
        state_numbers, state_energies = outputs.read_state_table(spectrum_path)
        # Match the solver's documented classify_states rule: states above the
        # midpoint between the minimum conduction edge and maximum valence edge
        # are electron-like. This removes diagonal, reverse, electron-electron,
        # and hole-hole rows from the all-pairs KP8 table.
        midpoint_eV = 0.5 * (
            float(np.min(band["conduction_eV"]))
            + float(
                max(
                    np.max(band["heavy_hole_eV"]),
                    np.max(band["light_hole_eV"]),
                    np.max(band["split_off_eV"]),
                )
            )
        )
        electron_states = {
            int(round(number))
            for number, energy in zip(state_numbers, state_energies)
            if float(energy) > midpoint_eV
        }
        hole_states = {
            int(round(number))
            for number, energy in zip(state_numbers, state_energies)
            if float(energy) <= midpoint_eV
        }
        transition_rows = [
            {
                "electron": i,
                "hole": j,
                "transition_energy_eV": float(values[energy_column]),
            }
            for (i, j), values in sorted(transitions.items())
            if i in electron_states
            and j in hole_states
            and float(values[energy_column]) > 0.0
        ]
        observables["kp8_classification_midpoint_eV"] = midpoint_eV
        observables["kp8_electron_states"] = sorted(electron_states)
        observables["kp8_hole_states"] = sorted(hole_states)
    else:
        transition_rows = [
            {
                "electron": i,
                "hole": j,
                "transition_energy_eV": float(values[energy_column]),
            }
            for (i, j), values in sorted(transitions.items())
            if float(values[energy_column]) > 0.0
        ]
    observables["transition_count"] = len(transition_rows)
    observables["transition_energies_eV"] = [
        row["transition_energy_eV"] for row in transition_rows
    ]
    if transition_rows:
        observables["lowest_transition_eV"] = min(
            row["transition_energy_eV"] for row in transition_rows
        )

    # --- overlaps -------------------------------------------------------------
    overlap_key = {
        "one_band": "overlap_integrals_gamma_hh",
        "kp6": "overlap_integrals_gamma_kp6",
        "kp8": "overlap_integrals_gamma_hh",
    }[band_model]
    overlaps = (
        _matrix_table(profile, raw, region, overlap_key)
        if band_model != "kp8"
        else None
    )
    if overlaps:
        overlap_column = outputs.first_value_column(overlaps, contains="|^2")
        for row in transition_rows:
            key = (int(row["electron"]), int(row["hole"]))
            row["overlap_squared"] = overlaps.get(key, {}).get(overlap_column)
        observables["maximum_overlap_squared"] = max(
            (
                float(row["overlap_squared"])
                for row in transition_rows
                if row.get("overlap_squared") is not None
            ),
            default=None,
        )

    # --- polarisation-resolved strengths -------------------------------------
    strength_key = (
        "oscillator_strengths_kp8" if band_model == "kp8" else "oscillator_strengths_gamma"
    )
    momentum_key = (
        "momentum_matrix_elements_kp8"
        if band_model == "kp8"
        else "momentum_matrix_elements_gamma"
    )
    strengths_by_polarization: dict[str, dict[tuple[int, int], float]] = {}
    momentum_by_polarization: dict[str, dict[tuple[int, int], float]] = {}
    momentum_units: dict[str, str] = {}
    for name in polarizations(cfg):
        table = _matrix_table(profile, raw, region, strength_key, polarization=name)
        if table:
            column = outputs.first_value_column(table, contains="f(")
            strengths_by_polarization[name] = {
                key: float(values[column]) for key, values in table.items()
            }
        momentum = _matrix_table(profile, raw, region, momentum_key, polarization=name)
        if momentum:
            resolved = outputs.resolve_outputs(
                profile,
                raw,
                [momentum_key],
                substitutions={"region": region, "polarization": name},
            )
            paths = resolved.many(momentum_key)
            if paths:
                momentum_column = outputs.magnitude_column(paths[0], unit="hbar/nm")
                momentum_by_polarization[name] = {
                    key: abs(float(values[momentum_column]))
                    for key, values in momentum.items()
                }
                momentum_units[name] = ";".join(
                    f"{column}={unit}"
                    for column, unit in outputs.matrix_element_units(paths[0]).items()
                )
    observables["momentum_matrix_element_units"] = momentum_units
    # Momentum and position matrix elements are different quantities with
    # different units (hbar/nm versus e*nm). They are recorded separately and
    # never added, subtracted, or plotted on one axis.
    validation["matrix_element_units_recorded"] = bool(momentum_units) or (
        band_model != "kp8"
    )

    for name, table in strengths_by_polarization.items():
        for row in transition_rows:
            electron = int(row["electron"])
            hole = int(row["hole"])
            # nextnano writes f(i,j) with the sign of E_j-E_i. Absorption is
            # the positive valence->conduction orientation (hole, electron).
            key = (hole, electron) if band_model == "kp8" else (electron, hole)
            row[f"oscillator_strength_{name}"] = table.get(key)
    for name, table in momentum_by_polarization.items():
        for row in transition_rows:
            electron = int(row["electron"])
            hole = int(row["hole"])
            key = (hole, electron) if band_model == "kp8" else (electron, hole)
            row[f"momentum_magnitude_{name}"] = table.get(key)

    observables["transition_rows"] = transition_rows
    observables["overlap_rows"] = [
        {
            "electron": row["electron"],
            "hole": row["hole"],
            "overlap_squared": row.get("overlap_squared"),
        }
        for row in transition_rows
        if row.get("overlap_squared") is not None
    ]

    if transition_rows:
        write_csv(
            extracted / "transitions.csv",
            {
                key: np.asarray([row.get(key) for row in transition_rows])
                for key in transition_rows[0]
            },
        )

    # --- diagnostic lineshape and solver optical spectrum --------------------
    diagnostic_spectra: dict[str, list[float]] = {}
    fraction = float(analysis_cfg.get("strong_transition_fraction", 0.10))
    for name in strengths_by_polarization:
        pairs = [
            (row["transition_energy_eV"], row.get(f"oscillator_strength_{name}"))
            for row in transition_rows
            if row.get(f"oscillator_strength_{name}") is not None
        ]
        if not pairs:
            continue
        grid, spectrum = lorentzian_spectrum(
            [pair[0] for pair in pairs],
            [abs(float(pair[1])) for pair in pairs],
            minimum_eV=float(numerical["spectral_energy_min_eV"]),
            maximum_eV=float(numerical["spectral_energy_max_eV"]),
            points=int(numerical["spectral_points"]),
            broadening_meV=float(numerical["broadening_meV"]),
        )
        diagnostic_spectra[name] = spectrum.tolist()
        diagnostic_spectra.setdefault("photon_energy_eV", grid.tolist())
        strongest = max(abs(float(pair[1])) for pair in pairs)
        observables[f"strong_transition_count_{name}"] = sum(
            1 for pair in pairs if abs(float(pair[1])) >= fraction * strongest
        )
        observables[f"strongest_oscillator_strength_{name}"] = strongest
        observables[f"suppressed_transition_count_{name}"] = sum(
            1 for pair in pairs if abs(float(pair[1])) < fraction * strongest
        )
    if diagnostic_spectra:
        write_json_atomically(
            extracted / "diagnostic_envelope_momentum_lineshape.json",
            {
                "units": SPECTRUM_UNITS,
                "broadening_meV": float(numerical["broadening_meV"]),
                "lineshape": "Lorentzian, FWHM = broadening_meV",
                "caveat": (
                    "Diagnostic only. The quantum-region KP8 momentum output is "
                    "the envelope momentum operator, not the full interband "
                    "Bloch/Kane optical response. Do not compare this curve to "
                    "an absorption spectrum."
                ),
                **diagnostic_spectra,
            },
        )

    solver_spectra: dict[str, list[float]] = {}
    absorption_paths: dict[str, str] = {}
    if band_model == "kp8":
        for name in polarizations(cfg):
            resolved_absorption = outputs.resolve_outputs(
                profile,
                raw,
                ["absorption_coefficient_quantum_spectra"],
                substitutions={"region": region, "polarization": name},
            )
            paths = resolved_absorption.many(
                "absorption_coefficient_quantum_spectra"
            )
            if not paths:
                continue
            table = outputs.read_table(paths[0])
            if table.n_columns < 2:
                raise outputs.ParserError(
                    f"{paths[0]}: expected photon energy and absorption coefficient."
                )
            energy = table.column(0)
            absorption = table.column(1)
            if "photon_energy_eV" in solver_spectra and not np.allclose(
                np.asarray(solver_spectra["photon_energy_eV"]),
                energy,
                rtol=0.0,
                atol=1e-12,
            ):
                raise outputs.ParserError(
                    "polarization-resolved absorption files use different energy grids."
                )
            solver_spectra.setdefault("photon_energy_eV", energy.tolist())
            solver_spectra[name] = absorption.tolist()
            absorption_paths[name] = str(paths[0])
            write_csv(
                extracted / f"absorption_{name}.csv",
                {
                    "photon_energy_eV": energy,
                    "absorption_coefficient_cm-1": absorption,
                },
            )
            observables[f"peak_absorption_cm-1_{name}"] = float(
                np.max(absorption)
            )
        if solver_spectra:
            write_csv(
                extracted / "absorption_spectrum.csv",
                {
                    name: np.asarray(values)
                    for name, values in solver_spectra.items()
                },
            )
            write_json_atomically(
                extracted / "absorption_spectrum.json",
                {
                    "units": "cm^-1",
                    "source": "nextnano++ optics{quantum_spectra{}}",
                    **solver_spectra,
                },
            )
            observables["spectrum_units"] = "cm^-1 (nextnano++ quantum_spectra)"
            observables["absorption_source_files"] = absorption_paths

    spectra = solver_spectra or diagnostic_spectra

    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))
    validation.update(
        {key: value for key, value in log_checks.items() if isinstance(value, bool)}
    )
    validation["transition_energies_present"] = bool(transition_rows)
    validation["transition_energies_finite"] = all(
        math.isfinite(float(row["transition_energy_eV"])) for row in transition_rows
    )
    if band_model == "kp8":
        validation["envelope_momentum_diagnostics_present"] = bool(
            strengths_by_polarization
        )
        expected_polarizations = set(polarizations(cfg))
        found_polarizations = set(solver_spectra) - {"photon_energy_eV"}
        validation["solver_absorption_present"] = (
            found_polarizations == expected_polarizations
        )
        validation["solver_absorption_finite"] = bool(solver_spectra) and all(
            np.isfinite(np.asarray(values, dtype=float)).all()
            for name, values in solver_spectra.items()
            if name != "photon_energy_eV"
        )
        validation["solver_absorption_nonzero"] = bool(solver_spectra) and any(
            float(np.max(np.abs(np.asarray(values, dtype=float)))) > 0.0
            for name, values in solver_spectra.items()
            if name != "photon_energy_eV"
        )

    _per_case_plots(
        cfg,
        model,
        transition_rows,
        spectra,
        plots_dir,
        solver_absorption=bool(solver_spectra),
    )
    return observables, validation


def _per_case_plots(
    cfg: Mapping[str, Any],
    model: Mapping[str, Any],
    transition_rows: Sequence[Mapping[str, Any]],
    spectra: Mapping[str, Sequence[float]],
    plots_dir: Path,
    *,
    solver_absorption: bool = False,
) -> None:
    if not cfg["outputs"].get("write_plots", True):
        return
    label = str(model.get("name"))
    if spectra and "photon_energy_eV" in spectra:
        series = {
            name: (spectra["photon_energy_eV"], values)
            for name, values in spectra.items()
            if name != "photon_energy_eV"
        }
        plotting.line_plot(
            plots_dir / "spectrum.png",
            title=(
                f"Solver interband absorption ({label})"
                if solver_absorption
                else f"Diagnostic envelope-momentum lineshape ({label})"
            ),
            xlabel="Photon energy (eV)",
            ylabel=(
                "Absorption coefficient (cm$^{-1}$)"
                if solver_absorption
                else "Diagnostic strength (arb. u.; not absorption)"
            ),
            series=series,
            markers=False,
        )
    if transition_rows:
        electrons = sorted({int(row["electron"]) for row in transition_rows})
        holes = sorted({int(row["hole"]) for row in transition_rows})
        matrix = np.full((len(electrons), len(holes)), np.nan)
        for row in transition_rows:
            matrix[
                electrons.index(int(row["electron"])), holes.index(int(row["hole"]))
            ] = float(row["transition_energy_eV"])
        plotting.matrix_heatmap(
            plots_dir / "transition_energy_map.png",
            title=f"Transition energies ({label})",
            matrix=matrix,
            labels=[str(index) for index in holes],
            colorbar_label="Transition energy (eV)",
        )


def model_case(
    cfg: Mapping[str, Any], model: Mapping[str, Any], case_id: str, **overrides: Any
) -> sweeps.CaseSpec:
    config = (
        sweeps.apply_overrides(cfg, overrides) if overrides else sweeps.copy_config(cfg)
    )
    config["models"] = [dict(model)]
    return sweeps.CaseSpec(
        case_id=case_id,
        label=str(model.get("name")) + (f" ({overrides})" if overrides else ""),
        swept=dict(overrides),
        config=config,
        metadata={"sweep_kind": "model_stage", "model": str(model.get("name"))},
    )


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    models = cfg.get("models") or []
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    sweep_model = next(
        (
            m
            for m in models
            if str(m["name"]) == str(analysis_cfg.get("sweep_model", ""))
        ),
        models[-1],
    )

    cases = [
        model_case(cfg, model, f"model_{index}_{str(model['name'])[:2]}")
        for index, model in enumerate(models, start=1)
    ]
    model_count = len(cases)
    # Symmetry-broken twin of the reference model: the comparison that shows a
    # suppressed transition gaining strength.
    broken = dict(sweep_model)
    broken["name"] = f"{sweep_model['name']}_symmetry_broken"
    broken["symmetry_broken"] = True
    cases.append(model_case(cfg, broken, "sym_broken"))
    for index, value in enumerate(sweep_cfg.get("well_width_nm", []), start=1):
        cases.append(
            model_case(cfg, sweep_model, f"w_{index:02d}_{sweeps.safe_token(value)}",
                       well_width_nm=value)
        )
    for index, value in enumerate(sweep_cfg.get("electric_field_kV_cm", []), start=1):
        cases.append(
            model_case(cfg, sweep_model, f"f_{index:02d}_{sweeps.safe_token(value)}",
                       electric_field_kV_cm=value)
        )
    # k-space and spectral-resolution convergence reruns of the reference model.
    cases.append(
        model_case(
            cfg,
            sweep_model,
            "kconv",
            k_parallel_num_points=int(analysis_cfg.get("k_convergence_num_points", 12)),
        )
    )
    cases.append(
        model_case(
            cfg,
            sweep_model,
            "specres",
            spectral_points=int(cfg["numerical"]["spectral_points"]) * 2 - 1,
        )
    )

    results: list[sweeps.CaseResult] = []
    for case in cases:
        results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=case,
                machine=context.machine,
                run_dir=context.parent / "runs" / case.case_id,
                render_values=render_values,
                analyse=analyse_case,
                dependency_report=context.dependency_report,
            )
        )

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_table(
        context.parent,
        "model_comparison",
        [
            {
                "model": result.observables.get("model") or result.spec.case_id,
                "band_model": result.observables.get("band_model"),
                "k_parallel": result.observables.get("k_parallel_enabled"),
                "transition_count": result.observables.get("transition_count"),
                "lowest_transition_eV": result.observables.get("lowest_transition_eV"),
                "maximum_overlap_squared": result.observables.get("maximum_overlap_squared"),
                "strong_TM": result.observables.get("strong_transition_count_TM_growth"),
                "strong_TE": result.observables.get("strong_transition_count_TE_inplane"),
                "suppressed_TM": result.observables.get(
                    "suppressed_transition_count_TM_growth"
                ),
                "suppressed_TE": result.observables.get(
                    "suppressed_transition_count_TE_inplane"
                ),
                "peak_absorption_TM_cm-1": result.observables.get(
                    "peak_absorption_cm-1_TM_growth"
                ),
                "peak_absorption_TE_cm-1": result.observables.get(
                    "peak_absorption_cm-1_TE_inplane"
                ),
                "status": result.status,
            }
            for result in results[:model_count]
        ],
    )
    sweeps.write_table(
        context.parent,
        "symmetry_comparison",
        [
            {
                "case": result.spec.case_id,
                "symmetry_broken": result.observables.get("symmetry_broken"),
                "transition_count": result.observables.get("transition_count"),
                "suppressed_TE": result.observables.get(
                    "suppressed_transition_count_TE_inplane"
                ),
                "suppressed_TM": result.observables.get(
                    "suppressed_transition_count_TM_growth"
                ),
                "peak_absorption_TE_cm-1": result.observables.get(
                    "peak_absorption_cm-1_TE_inplane"
                ),
                "peak_absorption_TM_cm-1": result.observables.get(
                    "peak_absorption_cm-1_TM_growth"
                ),
                "status": result.status,
            }
            for result in results
            if str(result.observables.get("model", "")).startswith(str(sweep_model["name"]))
            or result.spec.case_id == "sym_broken"
        ],
    )
    _sweep_plots(
        context.parent, results, model_count, str(sweep_model["name"])
    )
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure or licensed-only physics: every k·p model is "
            "Standard-only, so no home run can produce this."
        ),
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={
            "profile": cfg["outputs"].get("parser_profile"),
            "unconfirmed_patterns": list(UNVALIDATED_SYNTAX),
        },
        extra={
            "model_count": model_count,
            "spectrum_units": "cm^-1",
            "spectrum_method": (
                "nextnano++ optics{quantum_spectra{}} Fermi-golden-rule "
                "interband absorption; envelope-momentum lineshape retained "
                "separately as a diagnostic only"
            ),
            "interband_requires_eight_bands": (
                "measured at home: momentum_matrix_elements over separate one-band "
                "Gamma and HH solutions writes only Gamma_Gamma and HH_HH, never an "
                "interband element"
            ),
        },
    )
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            (
                "all four models produced a generated input",
                model_count >= 4,
                "one-band → 6-band → 8-band zone-centre → 8-band k-resolved",
            ),
            (
                "no case was discarded",
                len(results) == len(cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "transition energies present and finite",
                _all_true(results, "transition_energies_finite"),
                "energy alone never establishes that a transition is strong",
            ),
            (
                "solver interband absorption exists and is nonzero in the 8-band model",
                (
                    _all_true(results, "solver_absorption_present")
                    and _all_true(results, "solver_absorption_finite")
                    and _all_true(results, "solver_absorption_nonzero")
                ),
                "physical interband optics comes from optics{quantum_spectra{}}, "
                "not the envelope-momentum table",
            ),
            (
                "matrix-element units recorded from the file headers",
                _all_true(results, "matrix_element_units_recorded"),
                "momentum (ħ/nm) and position (e·nm) are never mixed",
            ),
            (
                "8-band state compositions are present and normalised",
                (
                    _all_true(results, "state_composition_present")
                    and _all_true(results, "state_composition_normalised")
                )
                if _all_true(results, "state_composition_present") is not None
                else None,
                "required before assigning conduction-, HH-, LH-, or SO-like character",
            ),
        ],
        notes=[
            "The spectrum is POST-PROCESSED: a Lorentzian sum over transition "
            f"energies weighted by oscillator strength. Units are {SPECTRUM_UNITS}. "
            "It is not an absorption coefficient and has no cm^-1 value.",
            "broadening_meV is the HWHM of each line and stands in for every "
            "mechanism the calculation omits — dephasing, phonons, interface "
            "roughness, width fluctuation. It is an input, not a result.",
            "Polarization convention: growth is along x, so [1,0,0] is TM and "
            "[0,1,0] is TE. Confirmed at home for the one-band intersubband case, "
            "where in-plane oscillator strength was exactly zero.",
            "A transition is only counted as strong when its strength clears "
            "strong_transition_fraction of the strongest transition in the same "
            "run — never on the basis of a favourable energy.",
        ],
        unvalidated_syntax=UNVALIDATED_SYNTAX,
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def _sweep_plots(
    parent: Path,
    results: Sequence[sweeps.CaseResult],
    model_count: int,
    reference_model_name: str,
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    model_results = results[:model_count]
    series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for result in model_results:
        energies = result.observables.get("transition_energies_eV") or []
        if energies:
            series[str(result.observables.get("model"))] = (
                list(range(1, len(energies) + 1)),
                [float(value) for value in energies],
            )
    plotting.line_plot(
        plots_dir / "model_comparison_transitions.png",
        title="Interband transition energies: one-band vs 6-band vs 8-band",
        xlabel="Transition index",
        ylabel="Transition energy (eV)",
        series=series,
    )
    field_series: dict[str, tuple[list[float], list[float]]] = {}
    for name in ("TM_growth", "TE_inplane"):
        xs: list[float] = []
        ys: list[float] = []
        for result in results:
            field = result.spec.swept.get("electric_field_kV_cm")
            value = result.observables.get(f"peak_absorption_cm-1_{name}")
            if field is None or value is None:
                continue
            xs.append(float(field))
            ys.append(float(value))
        field_series[name] = (xs, ys)
    plotting.line_plot(
        plots_dir / "absorption_vs_field.png",
        title="Peak solver absorption versus electric field",
        xlabel="Electric field (kV/cm)",
        ylabel="Peak absorption coefficient (cm$^{-1}$)",
        series=field_series,
    )
    reference = next(
        (
            result
            for result in model_results
            if result.observables.get("model") == reference_model_name
        ),
        None,
    )
    _state_composition_plot(plots_dir, reference)
    _overlap_plot(plots_dir, model_results)
    _matrix_element_plot(plots_dir, reference)
    _polarization_strength_plot(plots_dir, reference)
    _spectrum_plots(plots_dir, results, reference)


def _state_composition_plot(
    plots_dir: Path, result: sweeps.CaseResult | None
) -> None:
    import json
    import matplotlib.pyplot as plt

    target = plots_dir / "state_composition.png"
    if result is None:
        plotting.placeholder(target, "State composition of the 8-band states")
        return
    path = result.run_dir / "extracted" / "state_composition.json"
    if not path.is_file():
        plotting.placeholder(target, "State composition of the 8-band states")
        return
    rows = json.loads(path.read_text(encoding="utf-8"))
    components = sorted(
        {
            key
            for row in rows
            for key in row
            if key not in {"state", "character", "dominant_fraction"}
        }
    )
    if not rows or not components:
        plotting.placeholder(target, "State composition of the 8-band states")
        return
    states = np.asarray([int(row["state"]) for row in rows])
    bottom = np.zeros(len(rows), dtype=float)
    fig, ax = plt.subplots(figsize=(7.2, 4.7))
    for component in components:
        values = np.asarray([float(row.get(component, 0.0)) for row in rows])
        ax.bar(states, values, bottom=bottom, label=component)
        bottom += values
    ax.set(
        title="Eight-band state composition",
        xlabel="State",
        ylabel="Normalised component weight",
        ylim=(0.0, 1.05),
    )
    ax.legend(fontsize=7, ncol=4)
    plotting.save_figure(fig, target)


def _transition_matrix(
    rows: Sequence[Mapping[str, Any]], key: str
) -> tuple[np.ndarray, list[str], list[str]]:
    usable = [row for row in rows if row.get(key) is not None]
    if not usable:
        return np.empty((0, 0)), [], []
    electrons = sorted({int(row["electron"]) for row in usable})
    holes = sorted({int(row["hole"]) for row in usable})
    matrix = np.full((len(electrons), len(holes)), np.nan)
    for row in usable:
        matrix[
            electrons.index(int(row["electron"])),
            holes.index(int(row["hole"])),
        ] = float(row[key])
    return matrix, [f"h{value}" for value in holes], [f"e{value}" for value in electrons]


def _overlap_plot(
    plots_dir: Path, model_results: Sequence[sweeps.CaseResult]
) -> None:
    source = next(
        (
            result
            for result in reversed(model_results)
            if result.observables.get("overlap_rows")
        ),
        None,
    )
    rows = source.observables.get("transition_rows") if source is not None else []
    matrix, holes, electrons = _transition_matrix(rows or [], "overlap_squared")
    plotting.rectangular_heatmap(
        plots_dir / "electron_hole_overlap.png",
        title="Electron-hole envelope overlap squared",
        matrix=matrix,
        xlabels=holes,
        ylabels=electrons,
        xlabel="Hole state",
        ylabel="Electron state",
        colorbar_label="|<e|h>|²",
    )


def _matrix_element_plot(
    plots_dir: Path, result: sweeps.CaseResult | None
) -> None:
    rows = result.observables.get("transition_rows") if result is not None else []
    preferred = "momentum_magnitude_TM_growth"
    key = preferred if any(row.get(preferred) is not None for row in rows or []) else (
        "oscillator_strength_TM_growth"
    )
    matrix, holes, electrons = _transition_matrix(rows or [], key)
    plotting.rectangular_heatmap(
        plots_dir / "matrix_element_heatmap.png",
        title=(
            "TM momentum-matrix magnitude"
            if key == preferred
            else "TM oscillator strength"
        ),
        matrix=matrix,
        xlabels=holes,
        ylabels=electrons,
        xlabel="Hole-like state",
        ylabel="Electron-like state",
        colorbar_label=(
            "|p| (header units)" if key == preferred else "Oscillator strength"
        ),
    )


def _polarization_strength_plot(
    plots_dir: Path, result: sweeps.CaseResult | None
) -> None:
    import matplotlib.pyplot as plt

    target = plots_dir / "polarization_resolved_strengths.png"
    rows = result.observables.get("transition_rows") if result is not None else []
    usable = [
        row
        for row in rows or []
        if row.get("oscillator_strength_TM_growth") is not None
        or row.get("oscillator_strength_TE_inplane") is not None
    ]
    if not usable:
        plotting.placeholder(target, "Polarisation-resolved transition strengths")
        return
    labels = [f"e{row['electron']}-h{row['hole']}" for row in usable]
    positions = np.arange(len(usable), dtype=float)
    width = 0.38
    fig, ax = plt.subplots(figsize=(max(7.0, len(usable) * 0.45), 4.8))
    for offset, name in ((-width / 2, "TM_growth"), (width / 2, "TE_inplane")):
        ax.bar(
            positions + offset,
            [float(row.get(f"oscillator_strength_{name}") or 0.0) for row in usable],
            width,
            label=name,
        )
    ax.set_xticks(positions, labels, rotation=45, ha="right", fontsize=7)
    ax.set(
        title="Polarisation-resolved oscillator strengths",
        xlabel="Transition",
        ylabel="Oscillator strength (dimensionless)",
    )
    ax.legend()
    plotting.save_figure(fig, target)


def _spectrum_plots(
    plots_dir: Path,
    results: Sequence[sweeps.CaseResult],
    reference: sweeps.CaseResult | None,
) -> None:
    import json

    def spectrum(result: sweeps.CaseResult) -> dict[str, Any] | None:
        extracted = result.run_dir / "extracted"
        for filename in (
            "absorption_spectrum.json",
            "diagnostic_envelope_momentum_lineshape.json",
        ):
            path = extracted / filename
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        return None

    symmetric = reference if reference is not None and spectrum(reference) else None
    broken = next(
        (r for r in results if r.observables.get("symmetry_broken") and spectrum(r)),
        None,
    )
    series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for label, result in (("symmetric", symmetric), ("symmetry broken", broken)):
        if result is None:
            continue
        data = spectrum(result)
        if not data:
            continue
        grid = data.get("photon_energy_eV") or []
        for name, values in data.items():
            if name in {
                "photon_energy_eV",
                "units",
                "source",
                "broadening_meV",
                "lineshape",
                "caveat",
            }:
                continue
            series[f"{label}: {name}"] = (grid, values)
    plotting.line_plot(
        plots_dir / "spectrum_symmetry_broken.png",
        title="Interband absorption: symmetric versus symmetry-broken",
        xlabel="Photon energy (eV)",
        ylabel="Absorption coefficient (cm$^{-1}$)",
        series=series,
        markers=False,
    )
    reference_data = spectrum(reference) if reference is not None else None
    reference_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    if reference_data:
        grid = reference_data.get("photon_energy_eV") or []
        for name, values in reference_data.items():
            if name in {
                "photon_energy_eV",
                "units",
                "source",
                "broadening_meV",
                "lineshape",
                "caveat",
            }:
                continue
            reference_series[name] = (grid, values)
    plotting.line_plot(
        plots_dir / "spectrum.png",
        title="Reference nextnano++ interband absorption spectrum",
        xlabel="Photon energy (eV)",
        ylabel="Absorption coefficient (cm$^{-1}$)",
        series=reference_series,
        markers=False,
    )
    convergence = [r for r in results if r.spec.case_id == "kconv"]
    conv_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for name, values in reference_series.items():
        conv_series[f"reference: {name}"] = values
    for result in convergence:
        data = spectrum(result)
        if not data:
            continue
        grid = data.get("photon_energy_eV") or []
        for name, values in data.items():
            if name in {
                "photon_energy_eV",
                "units",
                "source",
                "broadening_meV",
                "lineshape",
                "caveat",
            }:
                continue
            conv_series[f"{result.spec.case_id}: {name}"] = (grid, values)
    plotting.line_plot(
        plots_dir / "k_convergence.png",
        title="Spectral convergence with in-plane k sampling",
        xlabel="Photon energy (eV)",
        ylabel="Absorption coefficient (cm$^{-1}$)",
        series=conv_series,
        markers=False,
    )
    resolution_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {
        f"reference: {name}": values for name, values in reference_series.items()
    }
    for result in results:
        if result.spec.case_id != "specres":
            continue
        data = spectrum(result)
        if not data:
            continue
        grid = data.get("photon_energy_eV") or []
        for name, values in data.items():
            if name in {
                "photon_energy_eV",
                "units",
                "source",
                "broadening_meV",
                "lineshape",
                "caveat",
            }:
                continue
            resolution_series[f"double resolution: {name}"] = (grid, values)
    plotting.line_plot(
        plots_dir / "spectral_resolution_check.png",
        title="Solver absorption under two photon-energy resolutions",
        xlabel="Photon energy (eV)",
        ylabel="Absorption coefficient (cm$^{-1}$)",
        series=resolution_series,
        markers=False,
    )


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        result.validation.get(key)
        for result in results
        if result.solver_success and key in result.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)
