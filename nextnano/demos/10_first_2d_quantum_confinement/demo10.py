"""Demo 10 — first 2D model: a rectangular GaAs/AlGaAs quantum wire.

A quantum well confines in one direction and leaves the other two free.  Etch it
into a narrow ridge and a second direction becomes confined too: the subbands of
the well split further, and the answer now depends on a mesh in *two*
directions at once.

That is the whole point of the demo, and it is mostly a numerical one.  A 2D
mesh can break a symmetry the structure does not have, can be anisotropic
without anyone noticing, and costs the product of two directions.  So the
physics is kept as simple as possible -- one-band Gamma effective mass, no
strain, no polarization, no excitons, four states -- and the effort goes into
mesh, domain, symmetry, and alignment tests.

STATUS: no 2D run has ever executed in this repository.  The Free edition at
home builds the 2D grid and then refuses to run it (1D only), so the deck's
syntax is confirmed and its output file names are not.
"""

from __future__ import annotations

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
    ("material_map.png", "2D material map"),
    ("conduction_band_map.png", "2D conduction-band map"),
    ("ground_state_density.png", "Ground-state probability density"),
    ("first_excited_density.png", "First excited-state probability density"),
    ("horizontal_slice.png", "Horizontal centre slice"),
    ("vertical_slice.png", "Vertical centre slice"),
    ("energy_vs_width.png", "Energy versus wire width"),
    ("mesh_convergence.png", "Mesh convergence"),
    ("domain_convergence.png", "Domain-padding convergence"),
    ("symmetry_error.png", "Symmetry-error diagnostic"),
    ("mesh_anisotropy.png", "Isotropic versus anisotropic mesh"),
    ("one_d_limit.png", "Wide-wire limit against the 1D quantum well"),
)

# Confirmed on the licensed laptop on 2026-07-30: 2D output is AVS/Express
# .fld (ASCII header + little-endian float64 blocks at declared byte offsets),
# dim1 varies fastest so a variable reshapes to (ny, nx), grid_y.dat exists
# beside grid_x.dat, and the probability file is probabilities_k00000.fld with
# a probabilities_shift_k00000.fld twin. The (ny, nx) ordering is not an
# assumption: it is the only one under which the density integrates to 1.
UNVALIDATED_SYNTAX: tuple[str, ...] = (
    "the integer-to-material encoding inside Structure/material_indices.txt",
)


def build_wire(cfg: Mapping[str, Any]) -> layers.Wire2D:
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.Wire2D(
        core_width_nm=float(scientific["wire_width_nm"]),
        core_height_nm=float(scientific["wire_height_nm"]),
        barrier_x_nm=float(scientific["lateral_barrier_nm"])
        + float(numerical["domain_padding_x_nm"]),
        barrier_y_nm=float(scientific["vertical_barrier_nm"])
        + float(numerical["domain_padding_y_nm"]),
        aluminum_fraction=float(scientific["aluminum_fraction"]),
        offset_x_nm=float(numerical["geometry_offset_x_nm"]),
        offset_y_nm=float(numerical["geometry_offset_y_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "wire"))


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    wire = build_wire(cfg)
    numerical = cfg["numerical"]
    dx = float(numerical["grid_spacing_x_nm"])
    dy = float(numerical["grid_spacing_y_nm"])
    exterior = float(numerical["exterior_grid_spacing_nm"])
    points = wire.estimated_grid_points(grid_spacing_x_nm=dx, grid_spacing_y_nm=dy)
    if points > 250_000:
        raise DemoError(
            f"this configuration implies about {points} grid points. Refusing to "
            "generate it: 2D cost is the product of both directions. Coarsen the "
            "mesh or shrink the padding."
        )
    return {
        "temperature_K": cfg["scientific"]["temperature_K"],
        "number_of_states": int(numerical["number_of_states"]),
        "quantum_region_name": region_name(cfg),
        "quantum_x_min_nm": f"{wire.domain_x_nm[0]:.9g}",
        "quantum_x_max_nm": f"{wire.domain_x_nm[1]:.9g}",
        "quantum_y_min_nm": f"{wire.domain_y_nm[0]:.9g}",
        "quantum_y_max_nm": f"{wire.domain_y_nm[1]:.9g}",
        "xgrid_lines": wire.grid_lines(
            "x", core_spacing_nm=dx, exterior_spacing_nm=exterior
        ),
        "ygrid_lines": wire.grid_lines(
            "y", core_spacing_nm=dy, exterior_spacing_nm=exterior
        ),
        "structure_regions": wire.structure_regions(contact_name="wire_contact"),
    }


def build_1d_reference_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    barrier = float(scientific["vertical_barrier_nm"]) + float(
        numerical["domain_padding_y_nm"]
    )
    active = float(numerical["grid_spacing_y_nm"])
    exterior = float(numerical["exterior_grid_spacing_nm"])
    alloy = float(scientific["aluminum_fraction"])
    return layers.build_stack(
        [
            layers.Layer(
                "left_outer_barrier", layers.ALGAAS, barrier, alloy, exterior
            ),
            layers.Layer(
                "well", layers.GAAS, float(scientific["wire_height_nm"]), None, active
            ),
            layers.Layer(
                "right_outer_barrier", layers.ALGAAS, barrier, alloy, exterior
            ),
        ],
        exterior_grid_spacing_nm=exterior,
    )


def render_values_1d(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stack = build_1d_reference_stack(cfg)
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(
        float(numerical["domain_padding_y_nm"])
    )
    return {
        "temperature_K": cfg["scientific"]["temperature_K"],
        "number_of_states": int(numerical["number_of_states"]),
        "quantum_start_nm": f"{start:.9g}",
        "quantum_end_nm": f"{end:.9g}",
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(contact_name="well_contact"),
    }


def analyse_1d_reference(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    run = quantum1d.parse_one_band_run(
        raw,
        profile=profile,
        region_name="well1d",
        bandedge_columns=cfg["outputs"]["bandedge_columns"],
    )
    energies = [float(value) for value in run.energies_eV]
    write_csv(
        extracted / "energies.csv",
        {
            "state": np.arange(1, len(energies) + 1),
            "energy_eV": np.asarray(energies),
        },
    )
    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=cfg["validation"].get("completion_markers", ()),
        fatal_markers=cfg["validation"].get("fatal_markers", ()),
        warning_markers=cfg["validation"].get(
            "convergence_warning_markers", ()
        ),
    )
    log_checks.update(outputs.completion_evidence(raw))
    validation = {
        key: value for key, value in log_checks.items() if isinstance(value, bool)
    }
    validation["energies_finite_and_ordered"] = bool(
        energies
        and np.all(np.isfinite(energies))
        and np.all(np.diff(energies) > 0)
    )
    return {
        "reference_dimension": "1D",
        "wire_height_nm": float(cfg["scientific"]["wire_height_nm"]),
        "E1_eV": energies[0] if energies else None,
        "E2_eV": energies[1] if len(energies) > 1 else None,
        "electron_energies_eV": energies,
    }, validation


def read_2d_field(path: Path, x_nm: np.ndarray, y_nm: np.ndarray) -> np.ndarray:
    """First variable of a 2D field file, as ``(y, x)``."""

    return read_2d_fields(path, x_nm, y_nm)[0]


def read_2d_fields(
    path: Path, x_nm: np.ndarray, y_nm: np.ndarray
) -> np.ndarray:
    """Read every variable of a 2D field file as ``(variable, y, x)``.

    nextnano++ writes 2D data as AVS/Express ``.fld``: an ASCII header followed
    by little-endian float64 blocks at byte offsets the header states. The
    header carries the dimensions, the coordinate axes, the variable count, and
    the labels, so nothing about the layout is guessed --
    :func:`outputs.read_avs_field` checks that the byte accounting closes and
    that the coordinate axes are monotonic before returning anything.

    The axes in the file are cross-checked against ``grid_x.dat`` /
    ``grid_y.dat`` here, so a mismatched pairing fails instead of silently
    transposing a map.
    """

    field = outputs.read_avs_field(path)
    if len(field.dims) != 2:
        raise outputs.ParserError(
            f"{path} declares ndim={len(field.dims)}; this demo is 2D only."
        )
    nx, ny = int(x_nm.size), int(y_nm.size)
    if field.dims != (nx, ny):
        raise outputs.ParserError(
            f"{path} declares dim1={field.dims[0]}, dim2={field.dims[1]}, but "
            f"grid_x.dat has {nx} points and grid_y.dat has {ny}."
        )
    # grid_x.dat / grid_y.dat are written as text with about six significant
    # figures, so they differ from the binary float64 coordinates by up to
    # ~5e-5 nm. The tolerance is set well above that rounding and far below any
    # real defect: a transposed or mispaired axis is wrong by nanometres.
    for axis, (declared, expected) in enumerate(
        zip(field.coords, (x_nm, y_nm)), start=1
    ):
        difference = float(np.max(np.abs(declared - expected)))
        if difference > 1.0e-3:
            raise outputs.ParserError(
                f"{path}: coord {axis} disagrees with the grid file by "
                f"{difference:.3g} nm (spans {declared[0]}..{declared[-1]} against "
                f"{expected[0]}..{expected[-1]})."
            )
    return np.stack(field.variables)


def read_2d_fields_native(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read a 2D field on **its own** axes, as ``(x_nm, y_nm, fields)``.

    Not every 2D output shares the quantum grid. Confirmed on the licensed run
    of 2026-07-30: with a 63 x 51 simulation grid, ``bandedges.fld`` came back
    124 x 100 -- the ``2n - 2`` doubled grid that lets a piecewise-constant band
    edge be drawn with sharp interfaces instead of being smeared across a cell.
    Material and region maps use the same doubled grid.

    Forcing those onto the quantum grid would either fail or, worse, silently
    resample a discontinuous quantity. Each field therefore carries its own
    coordinates, which is exactly what the ``.fld`` header provides.
    """

    field = outputs.read_avs_field(path)
    if len(field.dims) != 2:
        raise outputs.ParserError(
            f"{path} declares ndim={len(field.dims)}; this demo is 2D only."
        )
    return field.coords[0], field.coords[1], np.stack(field.variables)


def field_labels(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Variable names and units declared in a 2D field file's header."""

    field = outputs.read_avs_field(path)
    return field.labels, field.units


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    wire = build_wire(cfg)
    numerical = cfg["numerical"]
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    region = region_name(cfg)

    observables: dict[str, Any] = {
        "wire_width_nm": float(cfg["scientific"]["wire_width_nm"]),
        "wire_height_nm": float(cfg["scientific"]["wire_height_nm"]),
        "grid_spacing_x_nm": float(numerical["grid_spacing_x_nm"]),
        "grid_spacing_y_nm": float(numerical["grid_spacing_y_nm"]),
        "domain_padding_x_nm": float(numerical["domain_padding_x_nm"]),
        "domain_padding_y_nm": float(numerical["domain_padding_y_nm"]),
        "geometry_offset_x_nm": float(numerical["geometry_offset_x_nm"]),
        "geometry_offset_y_nm": float(numerical["geometry_offset_y_nm"]),
        "mesh_anisotropy": wire.mesh_anisotropy(
            grid_spacing_x_nm=float(numerical["grid_spacing_x_nm"]),
            grid_spacing_y_nm=float(numerical["grid_spacing_y_nm"]),
        ),
        "estimated_grid_points": wire.estimated_grid_points(
            grid_spacing_x_nm=float(numerical["grid_spacing_x_nm"]),
            grid_spacing_y_nm=float(numerical["grid_spacing_y_nm"]),
        ),
        "core_x_nm": list(wire.core_x_nm),
        "core_y_nm": list(wire.core_y_nm),
    }
    validation: dict[str, Any] = {}

    grids = outputs.resolve_outputs(profile, raw, ["grid_x", "grid_y"])
    outputs.require_or_diagnose(
        grids, raw, ["grid_x", "grid_y"], why="this is a 2D simulation"
    )
    # grid_x.dat / grid_y.dat are the human-readable axes and are used only to
    # cross-check the field files. Every calculation below uses the FULL-PRECISION
    # float64 axes from the .fld header instead: the text files carry about six
    # significant figures, and that rounding is enough to make a perfectly
    # mirror-symmetric mesh look asymmetric to the symmetry diagnostic.
    x_text = outputs.read_table(grids.one("grid_x")).column(0)
    y_text = outputs.read_table(grids.one("grid_y")).column(0)
    observables["grid_points_x"] = int(x_text.size)
    observables["grid_points_y"] = int(y_text.size)
    observables["grid_points_total"] = int(x_text.size * y_text.size)

    spectrum = outputs.resolve_outputs(
        profile, raw, ["energy_spectrum_gamma"], substitutions={"region": region}
    )
    _, energies = outputs.read_state_table(spectrum.one("energy_spectrum_gamma"))
    observables["electron_energies_eV"] = [float(value) for value in energies]
    observables["E1_eV"] = float(energies[0]) if energies.size else None
    observables["E2_eV"] = float(energies[1]) if energies.size > 1 else None
    if energies.size > 1:
        observables["E21_meV"] = float(1000.0 * (energies[1] - energies[0]))
    validation["energies_finite_and_ordered"] = bool(
        np.all(np.isfinite(energies)) and np.all(np.diff(energies) > 0)
    )
    write_csv(
        extracted / "energies.csv",
        {
            "state": np.arange(1, energies.size + 1),
            "energy_eV": energies,
        },
    )

    densities = outputs.resolve_outputs(
        profile, raw, ["probabilities_2d"], substitutions={"region": region}
    )
    outputs.require_or_diagnose(
        densities,
        raw,
        ["probabilities_2d"],
        why="output_states{ probabilities = yes } was requested in a 2D region",
    )
    density_fields: list[np.ndarray] = []
    x_nm, y_nm = x_text, y_text
    for path in densities.many("probabilities_2d"):
        # Cross-checks the field axes against the text grid, then hands back the
        # exact ones.
        density_fields.extend(read_2d_fields(path, x_text, y_text))
        field_x, field_y, _ = read_2d_fields_native(path)
        x_nm, y_nm = field_x, field_y
    if not density_fields:
        raise DemoError("no 2D probability-density fields were parsed.")
    observables["grid_axis_source"] = "probabilities .fld header (float64)"
    normalised_fields: list[np.ndarray] = []
    raw_integrals: list[float] = []
    for state_index, field in enumerate(density_fields, start=1):
        normalised_state, integral = analysis.normalise_density_2d(
            x_nm, y_nm, field
        )
        normalised_fields.append(normalised_state)
        raw_integrals.append(float(integral))
        write_csv(
            extracted / f"probability_density_state_{state_index}.csv",
            {
                "x_nm": np.tile(x_nm, y_nm.size),
                "y_nm": np.repeat(y_nm, x_nm.size),
                "probability_density_nm^-2": normalised_state.reshape(-1),
            },
        )
    normalised = normalised_fields[0]
    raw_integral = raw_integrals[0]
    mean_x, mean_y = analysis.centroid_2d(x_nm, y_nm, normalised)
    boundary = analysis.boundary_probability_2d(
        x_nm,
        y_nm,
        normalised,
        edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
    )
    observables.update(
        {
            "ground_state_raw_integral": raw_integral,
            "ground_state_centroid_x_nm": mean_x,
            "ground_state_centroid_y_nm": mean_y,
            "ground_state_boundary_probability": boundary,
            "parsed_probability_state_count": len(normalised_fields),
            "state_probability_raw_integrals": raw_integrals,
        }
    )
    validation["probability_normalized"] = all(
        abs(integral - 1.0)
        <= float(validation_cfg.get("normalization_tolerance", 1e-3))
        for integral in raw_integrals
    )
    validation["at_least_two_probability_states"] = len(normalised_fields) >= 2
    validation["boundary_probability_small"] = bool(
        boundary <= float(validation_cfg.get("maximum_boundary_probability", 1e-3))
    )

    # Symmetry is only a meaningful test when the geometry is centred.
    centred = (
        abs(float(numerical["geometry_offset_x_nm"])) < 1e-9
        and abs(float(numerical["geometry_offset_y_nm"])) < 1e-9
    )
    if centred:
        try:
            error_x = analysis.symmetry_error(x_nm, y_nm, normalised, axis="x")
            error_y = analysis.symmetry_error(x_nm, y_nm, normalised, axis="y")
        except analysis.AnalysisError as exc:
            observables["symmetry_error_reason"] = str(exc)
        else:
            observables["symmetry_error_x"] = error_x
            observables["symmetry_error_y"] = error_y
            limit = float(
                analysis_cfg.get(
                    "maximum_symmetry_error",
                    validation_cfg.get("maximum_symmetry_error", 0.02),
                )
            )
            validation["symmetric_geometry_gives_symmetric_state"] = bool(
                max(error_x, error_y) <= limit
            )
    else:
        observables["symmetry_error_reason"] = (
            "geometry deliberately shifted relative to the mesh; the symmetry "
            "test does not apply to this case"
        )

    horizontal_x, horizontal = analysis.slice_2d(x_nm, y_nm, normalised, axis="x")
    vertical_y, vertical = analysis.slice_2d(x_nm, y_nm, normalised, axis="y")
    np.savetxt(
        extracted / "horizontal_slice.csv",
        np.column_stack([horizontal_x, horizontal]),
        delimiter=",",
        header="x_nm,probability_density_nm-2",
        comments="",
    )
    np.savetxt(
        extracted / "vertical_slice.csv",
        np.column_stack([vertical_y, vertical]),
        delimiter=",",
        header="y_nm,probability_density_nm-2",
        comments="",
    )
    write_json_atomically(
        extracted / "grid.json",
        {
            "grid_points_x": int(x_nm.size),
            "grid_points_y": int(y_nm.size),
            "mesh_anisotropy": observables["mesh_anisotropy"],
            "field_storage_order": (
                "AVS/Express .fld, dim1 (x) varies fastest, so each variable "
                "reshapes to (ny, nx): row index over y, column index over x. "
                "Confirmed 2026-07-30 -- it is the only ordering under which the "
                "probability density integrates to 1 over the cross-section."
            ),
        },
    )

    conduction_fields = outputs.resolve_outputs(profile, raw, ["bandedges_2d"])
    validation["conduction_band_map_present"] = bool(
        conduction_fields.many("bandedges_2d")
    )
    if conduction_fields.many("bandedges_2d"):
        # On its own doubled grid, not the quantum grid -- see
        # read_2d_fields_native.
        band_x, band_y, band_maps = read_2d_fields_native(
            conduction_fields.many("bandedges_2d")[0]
        )
        conduction_map = band_maps[0]
        observables["band_map_grid_points_x"] = int(band_x.size)
        observables["band_map_grid_points_y"] = int(band_y.size)
        observables["band_map_on_quantum_grid"] = bool(
            band_x.size == x_nm.size and band_y.size == y_nm.size
        )
        write_csv(
            extracted / "conduction_band_map.csv",
            {
                "x_nm": np.tile(band_x, band_y.size),
                "y_nm": np.repeat(band_y, band_x.size),
                "conduction_band_eV": conduction_map.reshape(-1),
            },
        )
        if cfg["outputs"].get("write_plots", True):
            plotting.map_2d(
                plots_dir / "conduction_band_map.png",
                title="2D conduction-band map",
                x_nm=band_x,
                y_nm=band_y,
                values=conduction_map,
                colorbar_label="Conduction-band edge (eV)",
                contours={"GaAs core": (wire.core_x_nm, wire.core_y_nm)},
            )

    material_outputs = outputs.resolve_outputs(profile, raw, ["material_map_2d"])
    validation["material_map_present"] = bool(material_outputs.many("material_map_2d"))
    if material_outputs.many("material_map_2d"):
        material_x, material_y, material_maps = read_2d_fields_native(
            material_outputs.many("material_map_2d")[0]
        )
        material_map = material_maps[0]
        write_csv(
            extracted / "material_map.csv",
            {
                "x_nm": np.tile(material_x, material_y.size),
                "y_nm": np.repeat(material_y, material_x.size),
                "material_index": material_map.reshape(-1),
            },
        )
        # The integer legend lives in a separate text file; carrying it through
        # means the map can be read without guessing what 27 and 43 mean.
        legend = outputs.resolve_outputs(profile, raw, ["material_index_legend"])
        if legend.many("material_index_legend"):
            observables["material_index_legend"] = (
                legend.one("material_index_legend")
                .read_text(encoding="utf-8", errors="replace")
                .strip()
                .splitlines()
            )
        observables["material_indices_present"] = sorted(
            int(value) for value in np.unique(material_map)
        )
        if cfg["outputs"].get("write_plots", True):
            plotting.map_2d(
                plots_dir / "material_map.png",
                title="2D material-index map",
                x_nm=material_x,
                y_nm=material_y,
                values=material_map,
                colorbar_label="Material index",
                contours={"GaAs core": (wire.core_x_nm, wire.core_y_nm)},
            )

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

    if cfg["outputs"].get("write_plots", True):
        plotting.map_2d(
            plots_dir / "ground_state_density.png",
            title="Ground-state probability density",
            x_nm=x_nm,
            y_nm=y_nm,
            values=normalised,
            colorbar_label="Normalised density (nm$^{-2}$)",
            contours={"GaAs core": (wire.core_x_nm, wire.core_y_nm)},
        )
        if len(normalised_fields) > 1:
            plotting.map_2d(
                plots_dir / "first_excited_density.png",
                title="First-excited-state probability density",
                x_nm=x_nm,
                y_nm=y_nm,
                values=normalised_fields[1],
                colorbar_label="Normalised density (nm$^{-2}$)",
                contours={"GaAs core": (wire.core_x_nm, wire.core_y_nm)},
            )
        plotting.line_plot(
            plots_dir / "horizontal_slice.png",
            title="Horizontal centre slice",
            xlabel="x (nm)",
            ylabel="Normalised density (nm$^{-2}$)",
            series={"slice": (horizontal_x, horizontal)},
            markers=False,
        )
        plotting.line_plot(
            plots_dir / "vertical_slice.png",
            title="Vertical centre slice",
            xlabel="y (nm)",
            ylabel="Normalised density (nm$^{-2}$)",
            series={"slice": (vertical_y, vertical)},
            markers=False,
        )
    return observables, validation


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}

    cases: list[sweeps.CaseSpec] = [
        sweeps.CaseSpec(
            case_id="base",
            label="baseline geometry and mesh",
            swept={},
            config=sweeps.copy_config(cfg),
            metadata={"sweep_kind": "baseline"},
        )
    ]
    cases += sweeps.single_variable_cases(
        cfg, "wire_width_nm", sweep_cfg.get("wire_width_nm", []), prefix="w_"
    )
    cases += sweeps.single_variable_cases(
        cfg, "grid_spacing_x_nm", sweep_cfg.get("grid_spacing_x_nm", []), prefix="mx_"
    )
    cases += sweeps.single_variable_cases(
        cfg, "grid_spacing_y_nm", sweep_cfg.get("grid_spacing_y_nm", []), prefix="my_"
    )
    cases += sweeps.single_variable_cases(
        cfg, "domain_padding_x_nm", sweep_cfg.get("domain_padding_x_nm", []), prefix="px_"
    )
    cases += sweeps.single_variable_cases(
        cfg, "domain_padding_y_nm", sweep_cfg.get("domain_padding_y_nm", []), prefix="py_"
    )
    for index, pair in enumerate(analysis_cfg.get("anisotropy_cases") or [], start=1):
        dx, dy = float(pair[0]), float(pair[1])
        cases.append(
            sweeps.CaseSpec(
                case_id=f"aniso_{index:02d}",
                label=f"mesh dx={dx} nm, dy={dy} nm",
                swept={"grid_spacing_x_nm": dx, "grid_spacing_y_nm": dy},
                config=sweeps.apply_overrides(
                    cfg, {"grid_spacing_x_nm": dx, "grid_spacing_y_nm": dy}
                ),
                metadata={"sweep_kind": "mesh_anisotropy"},
            )
        )
    for index, offset in enumerate(analysis_cfg.get("alignment_offsets_nm") or [], start=1):
        cases.append(
            sweeps.CaseSpec(
                case_id=f"align_{index:02d}",
                label=f"geometry shifted by {offset} nm relative to the mesh",
                swept={"geometry_offset_x_nm": float(offset)},
                config=sweeps.apply_overrides(
                    cfg,
                    {
                        "geometry_offset_x_nm": float(offset),
                        "geometry_offset_y_nm": float(offset),
                    },
                ),
                metadata={"sweep_kind": "mesh_alignment"},
            )
        )
    wide = analysis_cfg.get("wide_limit_width_nm")
    if wide is not None:
        cases.append(
            sweeps.CaseSpec(
                case_id="wide_limit",
                label=f"wide-wire limit, width {wide} nm (compare with the 1D well)",
                swept={"wire_width_nm": float(wide)},
                config=sweeps.apply_override(cfg, "wire_width_nm", float(wide)),
                metadata={"sweep_kind": "one_dimensional_limit"},
            )
        )
    cases.append(
        sweeps.CaseSpec(
            case_id="reference_1d",
            label="one-dimensional finite-well reference",
            swept={},
            config=sweeps.copy_config(cfg),
            metadata={"sweep_kind": "one_dimensional_reference"},
        )
    )

    results: list[sweeps.CaseResult] = []
    for case in cases:
        one_dimensional = (
            case.metadata.get("sweep_kind") == "one_dimensional_reference"
        )
        results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=case,
                machine=context.machine,
                run_dir=context.parent / "runs" / case.case_id,
                render_values=(
                    render_values_1d if one_dimensional else render_values
                ),
                analyse=(
                    analyse_1d_reference if one_dimensional else analyse_case
                ),
                template_name=(
                    "wire_1d_reference.in.j2" if one_dimensional else None
                ),
                dependency_report=context.dependency_report,
            )
        )

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_table(
        context.parent,
        "mesh_tests",
        [
            {
                "case": result.spec.case_id,
                "kind": result.spec.metadata.get("sweep_kind"),
                "grid_spacing_x_nm": result.observables.get("grid_spacing_x_nm"),
                "grid_spacing_y_nm": result.observables.get("grid_spacing_y_nm"),
                "mesh_anisotropy": result.observables.get("mesh_anisotropy"),
                "grid_points_total": result.observables.get("grid_points_total")
                or result.observables.get("estimated_grid_points"),
                "E1_eV": result.observables.get("E1_eV"),
                "E2_eV": result.observables.get("E2_eV"),
                "symmetry_error_x": result.observables.get("symmetry_error_x"),
                "symmetry_error_y": result.observables.get("symmetry_error_y"),
                "boundary_probability": result.observables.get(
                    "ground_state_boundary_probability"
                ),
                "runtime_seconds": result.runtime_seconds,
                "status": result.status,
            }
            for result in results
        ],
    )
    _sweep_plots(context.parent, results)
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "2D execution is licensed-only: the Free edition builds the 2D grid "
            "and then refuses to run it. No home run can produce this."
        ),
    )

    mesh_results = [
        result
        for result in results
        if result.spec.metadata.get("sweep_kind") == "mesh_anisotropy"
    ]
    alignment_results = [
        result
        for result in results
        if result.spec.metadata.get("sweep_kind") == "mesh_alignment"
    ]
    alignment_shift: float | None = None
    base = next((r for r in results if r.spec.case_id == "base"), None)
    if base is not None and base.observables.get("E1_eV") is not None:
        shifts = [
            abs(1000.0 * (float(r.observables["E1_eV"]) - float(base.observables["E1_eV"])))
            for r in alignment_results
            if r.observables.get("E1_eV") is not None
        ]
        alignment_shift = max(shifts) if shifts else None

    def finest_pair_change_meV(parameter: str, *, larger_is_finer: bool) -> float | None:
        points = [
            (
                float(result.spec.swept[parameter]),
                float(result.observables["E1_eV"]),
            )
            for result in results
            if result.spec.metadata.get("sweep_parameter") == parameter
            and result.observables.get("E1_eV") is not None
        ]
        if len(points) < 2:
            return None
        points.sort(key=lambda item: item[0], reverse=larger_is_finer)
        return abs(1000.0 * (points[0][1] - points[1][1]))

    mesh_x_change = finest_pair_change_meV(
        "grid_spacing_x_nm", larger_is_finer=False
    )
    mesh_y_change = finest_pair_change_meV(
        "grid_spacing_y_nm", larger_is_finer=False
    )
    padding_x_change = finest_pair_change_meV(
        "domain_padding_x_nm", larger_is_finer=True
    )
    padding_y_change = finest_pair_change_meV(
        "domain_padding_y_nm", larger_is_finer=True
    )
    anisotropy_energies = [
        float(result.observables["E1_eV"])
        for result in mesh_results
        if result.observables.get("E1_eV") is not None
    ]
    anisotropy_range_meV = (
        1000.0 * (max(anisotropy_energies) - min(anisotropy_energies))
        if len(anisotropy_energies) >= 2
        else None
    )
    wide_result = next(
        (
            result
            for result in results
            if result.spec.metadata.get("sweep_kind")
            == "one_dimensional_limit"
        ),
        None,
    )
    reference_1d = next(
        (
            result
            for result in results
            if result.spec.metadata.get("sweep_kind")
            == "one_dimensional_reference"
        ),
        None,
    )
    one_d_limit_shift_meV: float | None = None
    if (
        wide_result is not None
        and reference_1d is not None
        and wide_result.observables.get("E1_eV") is not None
        and reference_1d.observables.get("E1_eV") is not None
    ):
        one_d_limit_shift_meV = abs(
            1000.0
            * (
                float(wide_result.observables["E1_eV"])
                - float(reference_1d.observables["E1_eV"])
            )
        )
    sweeps.write_table(
        context.parent,
        "one_d_limit_comparison",
        [
            {
                "wide_wire_width_nm": (
                    wide_result.spec.swept.get("wire_width_nm")
                    if wide_result is not None
                    else None
                ),
                "wide_wire_E1_eV": (
                    wide_result.observables.get("E1_eV")
                    if wide_result is not None
                    else None
                ),
                "one_d_reference_E1_eV": (
                    reference_1d.observables.get("E1_eV")
                    if reference_1d is not None
                    else None
                ),
                "absolute_difference_meV": one_d_limit_shift_meV,
            }
        ],
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
            "case_count": len(cases),
            "mesh_anisotropy_cases": len(mesh_results),
            "alignment_cases": len(alignment_results),
            "maximum_alignment_energy_shift_meV": alignment_shift,
            "wide_wire_to_1d_energy_shift_meV": one_d_limit_shift_meV,
            "mesh_x_finest_pair_change_meV": mesh_x_change,
            "mesh_y_finest_pair_change_meV": mesh_y_change,
            "padding_x_largest_pair_change_meV": padding_x_change,
            "padding_y_largest_pair_change_meV": padding_y_change,
            "anisotropy_energy_range_meV": anisotropy_range_meV,
            "invariant_direction": (
                "the third direction is assumed translationally invariant; the "
                "wire is infinitely long and free-electron-like along it"
            ),
            "field_storage_order": (
                "AVS/Express .fld, dim1 (x) fastest -> (ny, nx). Confirmed "
                "2026-07-30 by the density integrating to 1."
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
                "every requested test produced a generated input",
                all((result.run_dir / "generated_input").is_dir() for result in results),
                f"{len(results)} cases: width, mesh, anisotropy, padding, alignment, 1D limit",
            ),
            (
                "no case was discarded",
                len(results) == len(cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "a symmetric geometry gives a symmetric ground state",
                _all_true(results, "symmetric_geometry_gives_symmetric_state"),
                "reflection asymmetry against maximum_symmetry_error",
            ),
            (
                "sub-cell translation does not move the energy",
                None
                if alignment_shift is None
                else alignment_shift
                <= float(cfg["validation"]["absolute_energy_tolerance_meV"]),
                f"largest shift: "
                f"{'not evaluated' if alignment_shift is None else f'{alignment_shift:.4f} meV'}",
            ),
            (
                "boundary probability negligible",
                _all_true(results, "boundary_probability_small"),
                "probability inside a 5 % frame around the domain",
            ),
            (
                "probability densities normalised",
                _all_true(results, "probability_normalized"),
                "2D integral over the cross-section",
            ),
            (
                "ground and first-excited probability maps are present",
                _all_true(results, "at_least_two_probability_states"),
                "both are required evidence outputs",
            ),
            (
                "material and conduction-band maps are present",
                (
                    _all_true(results, "material_map_present")
                    and _all_true(results, "conduction_band_map_present")
                )
                if _all_true(results, "material_map_present") is not None
                else None,
                "confirms that the solved confinement matches the intended 2D heterostructure",
            ),
            (
                "energies finite and ordered",
                _all_true(results, "energies_finite_and_ordered"),
                "",
            ),
            (
                "finest x and y meshes agree",
                None
                if mesh_x_change is None or mesh_y_change is None
                else max(mesh_x_change, mesh_y_change)
                <= float(cfg["validation"]["absolute_energy_tolerance_meV"]),
                f"x={mesh_x_change}, y={mesh_y_change} meV",
            ),
            (
                "largest x and y domain paddings agree",
                None
                if padding_x_change is None or padding_y_change is None
                else max(padding_x_change, padding_y_change)
                <= float(cfg["validation"]["absolute_energy_tolerance_meV"]),
                f"x={padding_x_change}, y={padding_y_change} meV",
            ),
            (
                "anisotropic meshes do not materially move E1",
                None
                if anisotropy_range_meV is None
                else anisotropy_range_meV
                <= float(
                    analysis_cfg.get(
                        "maximum_anisotropy_energy_shift_meV", 2.0
                    )
                ),
                f"range={anisotropy_range_meV} meV",
            ),
            (
                "wide 2D wire approaches the matching 1D finite well",
                None
                if one_d_limit_shift_meV is None
                else one_d_limit_shift_meV
                <= float(
                    analysis_cfg.get(
                        "wide_limit_tolerance_meV",
                        cfg["validation"].get(
                            "absolute_energy_tolerance_meV", 1.0
                        ),
                    )
                ),
                f"|E1(wide 2D) - E1(1D)| = "
                f"{'not evaluated' if one_d_limit_shift_meV is None else f'{one_d_limit_shift_meV:.4f} meV'}",
            ),
        ],
        notes=[
            "The third direction is assumed translationally invariant: this is an "
            "infinitely long wire, free-electron-like along its axis. The 2D "
            "eigenvalues are the subband edges of that dispersion, not total "
            "energies.",
            "Mesh anisotropy is reported for every case, including the isotropic "
            "ones, so a silently anisotropic mesh cannot hide.",
            "The alignment cases shift the geometry by a fraction of a cell "
            "relative to the mesh. A symmetric structure must not gain energy "
            "from where the grid happens to fall.",
            "The wide-wire case is compared with the dedicated 1D finite-well "
            "reference solved in this same demo at the same vertical height: "
            "lateral confinement should become negligible and the subband edge "
            "should approach the 1D result.",
            "2D is expensive because the mesh cost is the product of two "
            "directions and the eigenproblem grows with it. The generator refuses "
            "configurations above 250,000 grid points rather than letting a "
            "typo run for hours.",
            "Nothing here is an electromagnetic calculation. No optical mode, "
            "waveguide mode, or resonance is being solved — only the electron "
            "envelope in a 2D cross-section.",
        ],
        unvalidated_syntax=UNVALIDATED_SYNTAX,
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def _series(
    results: Sequence[sweeps.CaseResult], parameter: str, observable: str
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for result in results:
        value = result.observables.get(observable)
        swept = result.spec.swept.get(parameter)
        if value is None or swept is None:
            continue
        xs.append(float(swept))
        ys.append(float(value))
    return xs, ys


def _sweep_plots(parent: Path, results: Sequence[sweeps.CaseResult]) -> None:
    import shutil

    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    base = next((result for result in results if result.spec.case_id == "base"), None)
    if base is not None:
        for filename in (
            "material_map.png",
            "conduction_band_map.png",
            "ground_state_density.png",
            "first_excited_density.png",
            "horizontal_slice.png",
            "vertical_slice.png",
        ):
            source = base.run_dir / "plots" / filename
            if source.is_file():
                shutil.copy2(source, plots_dir / filename)
    plotting.line_plot(
        plots_dir / "energy_vs_width.png",
        title="Subband energies versus wire width",
        xlabel="Wire width (nm)",
        ylabel="Energy (eV)",
        series={
            "E1": _series(results, "wire_width_nm", "E1_eV"),
            "E2": _series(results, "wire_width_nm", "E2_eV"),
        },
    )
    plotting.line_plot(
        plots_dir / "mesh_convergence.png",
        title="E1 versus mesh spacing",
        xlabel="Grid spacing (nm)",
        ylabel="E1 (eV)",
        series={
            "x refinement": _series(results, "grid_spacing_x_nm", "E1_eV"),
            "y refinement": _series(results, "grid_spacing_y_nm", "E1_eV"),
        },
    )
    plotting.line_plot(
        plots_dir / "domain_convergence.png",
        title="E1 versus domain padding",
        xlabel="Padding (nm)",
        ylabel="E1 (eV)",
        series={
            "x padding": _series(results, "domain_padding_x_nm", "E1_eV"),
            "y padding": _series(results, "domain_padding_y_nm", "E1_eV"),
        },
    )
    symmetry = [
        (result.spec.case_id, result.observables.get("symmetry_error_x"))
        for result in results
        if result.observables.get("symmetry_error_x") is not None
    ]
    plotting.bar_plot(
        plots_dir / "symmetry_error.png",
        title="Reflection asymmetry of the ground state (should be ~0)",
        xlabel="Case",
        ylabel="max|f − Pf| / max|f|",
        labels=[name for name, _ in symmetry],
        values=[float(value) for _, value in symmetry],
    )
    anisotropy = [
        (
            result.spec.case_id,
            result.observables.get("mesh_anisotropy"),
            result.observables.get("E1_eV"),
        )
        for result in results
        if result.spec.metadata.get("sweep_kind") == "mesh_anisotropy"
        and result.observables.get("E1_eV") is not None
    ]
    plotting.line_plot(
        plots_dir / "mesh_anisotropy.png",
        title="E1 versus mesh anisotropy (max/min spacing ratio)",
        xlabel="Mesh anisotropy",
        ylabel="E1 (eV)",
        series={
            "E1": (
                [float(item[1]) for item in anisotropy],
                [float(item[2]) for item in anisotropy],
            )
        },
    )
    reference = next(
        (
            result
            for result in results
            if result.spec.metadata.get("sweep_kind")
            == "one_dimensional_reference"
        ),
        None,
    )
    width_points = [
        (
            float(result.spec.swept["wire_width_nm"]),
            float(result.observables["E1_eV"]),
        )
        for result in results
        if result.spec.swept.get("wire_width_nm") is not None
        and result.observables.get("E1_eV") is not None
    ]
    reference_series: tuple[list[float], list[float]] = ([], [])
    if reference is not None and reference.observables.get("E1_eV") is not None and width_points:
        width_values = [point[0] for point in width_points]
        reference_energy = float(reference.observables["E1_eV"])
        reference_series = (
            [min(width_values), max(width_values)],
            [reference_energy, reference_energy],
        )
    plotting.line_plot(
        plots_dir / "one_d_limit.png",
        title="Wide-wire limit — compare with the 1D quantum well of the same height",
        xlabel="Wire width (nm)",
        ylabel="E1 (eV)",
        series={
            "E1": (
                [point[0] for point in width_points],
                [point[1] for point in width_points],
            ),
            "matching 1D finite well": reference_series,
        },
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
