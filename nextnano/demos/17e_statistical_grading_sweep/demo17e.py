"""Demo 17E scientific core: 21 licensed solves, one variable, two scales.

WHAT THIS MODULE OWNS
=====================
Very little physics, on purpose. The geometry builder is Demo 14's, the
composition renderer and its realized-composition gate are Demo 16E's, the
solver invocation is Demo 16B's, Eq. 2 is Demo 11's, and the three absolute-scale
corrections are Demo 17's -- imported from ``demo17`` and re-verified by its own
functions rather than re-implemented here. Reimplementing any of them is the one
way to accidentally change what is being compared.

What Demo 17E adds is three things:

``the deck for 21 realizations``
    :func:`build_case` drives Demo 17's template with per-case sampled interface
    widths instead of Demo 17's ten hand-written geometries.

``the dual reporting scale``
    :class:`CalibrationScale` and :func:`scaled_optics`. Every optical number is
    written twice -- raw (1.0x, nothing fitted, the only scale that follows from
    cited physics end to end) and calibrated (raw times ONE declared multiplier
    carried from Demo 17D). The calibrated column exists so the pm/V figures sit
    on the same axis as the paper's; it does not validate the scale, and
    :func:`calibration_record` stamps that status beside every calibrated number
    written anywhere.

``the roughness statistics``
    :func:`roughness_statistics` and :func:`grading_trend`, which are the point
    of the demo: a slope and a spread of chi(2) against interface grading width,
    over a controlled ensemble where nothing else moved.

NO GATE, CHECK OR VERDICT ANYWHERE IN THIS MODULE READS A CALIBRATED NUMBER.
Calibration is a presentation layer applied after every check has run.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import statistics as pystats
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import cases17e
import demo14
import demo16b
import demo16e
import demo17
import grading14
import runlog14

DEMO_DIR = Path(__file__).resolve().parent
DEMO_ID = cases17e.DEMO_ID
DEMO_VERSION = "demo17e-1.0.0"
CONFIG_FILENAME = cases17e.CONFIG_FILENAME
TARGET_WAVELENGTH_NM = cases17e.TARGET_WAVELENGTH_NM

#: Conventions and labels reused verbatim, so a Demo 17E table, a Demo 17 table
#: and a Demo 16E table mean the same thing column for column.
STATE_LABELS = demo16e.STATE_LABELS
REGION_LABELS = demo16e.REGION_LABELS
LOCALIZATION_CONVENTION = demo16e.LOCALIZATION_CONVENTION
HOLE_ENERGY_CONVENTION = demo16e.HOLE_ENERGY_CONVENTION

#: The named 2x2 elements Eq. 2 consumes, as Demo 11 records them.
MATRIX_ELEMENT_KEYS = (
    "overlap_e1_hh1", "overlap_e2_hh2",
    "z_e1_e1_nm", "z_e1_e2_nm", "z_e2_e2_nm",
    "z_hh1_hh1_nm", "z_hh1_hh2_nm", "z_hh2_hh2_nm",
    "electron_hole_centroid_separation_nm",
)

#: Independently computed here so the per-case settings check has its own source
#: of truth rather than reading its expectation out of the thing it is checking.
EXPECTED_N_Z_PER_M = 2.0 / 30.0e-9
EXPECTED_K_MAX_PER_NM = 0.10 * 2.0 * math.pi / 0.565325


class Demo17EError(RuntimeError):
    """A Demo 17E construction that is wrong rather than merely unusual."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Demo 17E's config, held to Demo 14's schema and Demo 17's corrections.

    ``demo17.load_config`` is called rather than copied: it runs Demo 14's
    validation and then the three correction verifiers, so 17E's config has to
    clear exactly the bar Demo 17's did. What is added on top is 17E's own two
    blocks -- the sampling plan and the prefactor scales -- both verified here
    because Demo 17's schema has no opinion about either.
    """

    cfg = demo17.load_config(Path(path) if path else DEMO_DIR / CONFIG_FILENAME)
    if str(cfg["experiment"].get("demo_id")) != DEMO_ID:
        raise Demo17EError(
            f"config declares demo_id {cfg['experiment'].get('demo_id')!r}, not "
            f"{DEMO_ID!r}; a run would be filed under the wrong demo."
        )
    # Both raise on anything malformed, so a bad sampling plan or a prefactor
    # whose arithmetic does not close is refused before any licensed time is
    # spent rather than after 21 solves.
    cases17e.sampling_plan_from_config(cfg)
    load_calibrations(cfg)
    verify_wavelength_grid(cfg)
    return cfg


def verify_wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    """The 1400-1800 nm evaluation grid must land on exactly 1 nm.

    Every spectral artifact in this demo -- the per-case CSVs, the all-case
    matrix, the standard-deviation bands -- differences curves point by point,
    which is only meaningful if all 21 sit on one grid. A grid that is not the
    declared 1 nm would still plot, and the bands would silently be wrong.
    """

    window = cfg["chi2"]["focused_wavelength_nm"]
    points = int(cfg["chi2"]["focused_wavelength_points"])
    start, stop = float(window[0]), float(window[1])
    if points < 2 or stop <= start:
        raise Demo17EError(
            f"chi2.focused_wavelength_nm {window} with {points} points is not a "
            "usable grid."
        )
    step = (stop - start) / (points - 1)
    if not math.isclose(step, 1.0, rel_tol=1e-12):
        raise Demo17EError(
            f"the focused grid steps {step:.6f} nm, not the 1.0 nm this demo's "
            f"spectral CSV and its standard-deviation bands assume. "
            f"{int(round(stop - start)) + 1} points would give exactly 1 nm."
        )
    return np.linspace(start, stop, points)


def wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    return verify_wavelength_grid(cfg)


# ---------------------------------------------------------------------------
# The dual reporting scale
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationScale:
    """One declared multiplier, and exactly what backs it.

    ``status`` is carried over from Demo 17b's verdict vocabulary and is never
    upgraded here: ``established`` means a cited source requires the factor,
    ``speculative`` means nothing in this repository establishes it, and
    ``contradicted`` means a measurement in this repository points the other way.
    A scale is applied because the config asked for it, never because its status
    is good.
    """

    scale_id: str
    label: str
    multiplier: float
    status: str
    source: str
    factors: Mapping[str, float] | None = None

    @property
    def is_raw(self) -> bool:
        return self.multiplier == 1.0

    def apply(self, value: float | None) -> float | None:
        return None if value is None else float(value) * float(self.multiplier)

    def as_record(self) -> dict[str, Any]:
        return {
            "scale_id": self.scale_id,
            "label": self.label,
            "multiplier": self.multiplier,
            "status": self.status,
            "source": self.source,
            "factors": dict(self.factors) if self.factors else None,
            "is_raw": self.is_raw,
        }


#: Stamped beside every calibrated number this demo writes. Demo 17D's own
#: finding, restated where it cannot be missed.
CALIBRATION_WARNING = (
    "A calibrated value is the raw value times ONE DECLARED multiplier. The "
    "multiplier is not derived here and was not derived by Demo 17D either: that "
    "sweep resolves the PRODUCT of four hypothesised factors and can never "
    "attribute it, two of its ten combinations reach the same total by different "
    "routes, and combination 10 was constructed from the known 27.63x residual so "
    "its landing on the published anchor is arithmetic rather than evidence. The "
    "calibrated column puts this demo's numbers on the paper's axis. It does not "
    "validate the scale, and no gate, check or verdict in this demo reads it."
)

RAW_UNITS = "pm/V (Demo 17-corrected Eq. 2, no multiplier)"
CALIBRATED_UNITS = "pm/V (raw x a declared Demo 17D multiplier)"


def load_calibrations(cfg: Mapping[str, Any]) -> dict[str, CalibrationScale]:
    """Every scale the config declares, with its arithmetic checked.

    A declared ``multiplier`` that does not equal the product of its own stated
    factors is refused rather than applied, for the same reason Demo 17D refuses
    one: a typo in the table would otherwise print a multiplier the numbers were
    not computed with.
    """

    block = cfg.get("prefactor")
    if not isinstance(block, Mapping):
        raise Demo17EError(
            f"{CONFIG_FILENAME} has no 'prefactor' block; Demo 17E reports a raw "
            "and a calibrated scale and must be told what the calibrated one is."
        )
    raw_cfg = block.get("raw") or {}
    scales: dict[str, CalibrationScale] = {
        "raw": CalibrationScale(
            scale_id="raw",
            label=str(raw_cfg.get("label", "Raw Baseline")),
            multiplier=float(raw_cfg.get("multiplier", 1.0)),
            status=str(raw_cfg.get("status", "established")),
            source=str(raw_cfg.get("source", "")).strip(),
        )
    }
    if scales["raw"].multiplier != 1.0:
        raise Demo17EError(
            f"prefactor.raw.multiplier is {scales['raw'].multiplier}, not 1.0. The "
            "raw column is the unscaled baseline by definition; a raw scale that "
            "multiplies is not a baseline."
        )
    verify_products = bool(block.get("verify_factor_products", True))
    tolerance = float(block.get("factor_product_tolerance", 1e-9))
    for scale_id, entry in (block.get("scales") or {}).items():
        multiplier = float(entry["multiplier"])
        factors = entry.get("factors")
        if verify_products and factors:
            product = 1.0
            for value in factors.values():
                product *= float(value)
            if not math.isclose(product, multiplier, rel_tol=tolerance, abs_tol=1e-12):
                raise Demo17EError(
                    f"prefactor scale {scale_id!r} declares {multiplier:g}x but its "
                    f"factors multiply to {product:g} "
                    f"({' x '.join(f'{v:g}' for v in factors.values())}). Fix the "
                    "table; this demo will not report a multiplier the numbers "
                    "were not computed with."
                )
        if multiplier <= 0:
            raise Demo17EError(f"prefactor scale {scale_id!r} must be positive.")
        scales[str(scale_id)] = CalibrationScale(
            scale_id=str(scale_id),
            label=str(entry.get("label", scale_id)),
            multiplier=multiplier,
            status=str(entry.get("status", "speculative")),
            source=str(entry.get("source", "")).strip(),
            factors={k: float(v) for k, v in (factors or {}).items()} or None,
        )
    active = str(block.get("active", "raw"))
    if active not in scales:
        raise Demo17EError(
            f"prefactor.active is {active!r}, which is not one of "
            f"{sorted(scales)}."
        )
    return scales


def active_calibration(
    cfg: Mapping[str, Any], override: str | None = None
) -> CalibrationScale:
    """The scale the calibrated column uses for this run."""

    scales = load_calibrations(cfg)
    key = str(override or (cfg.get("prefactor") or {}).get("active", "raw"))
    if key not in scales:
        raise Demo17EError(
            f"unknown calibration {key!r}; this config declares {sorted(scales)}."
        )
    return scales[key]


def calibration_record(
    cfg: Mapping[str, Any], calibration: CalibrationScale
) -> dict[str, Any]:
    """Everything about the reporting scales, for stamping into artifacts."""

    scales = load_calibrations(cfg)
    return {
        "raw": scales["raw"].as_record(),
        "raw_units": RAW_UNITS,
        "active_calibration": calibration.as_record(),
        "calibrated_units": CALIBRATED_UNITS,
        "available_scales": {
            key: scale.as_record() for key, scale in sorted(scales.items())
        },
        "raw_column_is_fitted": False,
        "calibrated_column_is_declared_not_derived": True,
        "calibration_used_in_any_gate_or_check": False,
        "warning": CALIBRATION_WARNING,
    }


def scaled_optics(
    optical: Mapping[str, Any], calibration: CalibrationScale
) -> dict[str, Any]:
    """The raw pair and the calibrated pair, side by side and both labelled.

    Wavelengths are NOT scaled: a multiplier moves the amplitude of a spectrum
    and cannot move its peak. That the peak wavelength is identical in both
    columns is the point -- it is the part of the reproduction a prefactor
    argument can never touch.
    """

    raw_1550 = optical.get("chi2_at_1550")
    raw_peak = optical.get("spectral_peak_chi2")
    return {
        "chi2_1550_raw_pm_per_V": raw_1550,
        "chi2_1550_calibrated_pm_per_V": calibration.apply(raw_1550),
        "peak_chi2_raw_pm_per_V": raw_peak,
        "peak_chi2_calibrated_pm_per_V": calibration.apply(raw_peak),
        "peak_wavelength_nm": optical.get("spectral_peak_wavelength_nm"),
        "detuning_from_1550_nm": optical.get("detuning_from_1550_nm"),
        "peak_over_1550_contrast": (
            None if not raw_1550 or raw_peak is None
            else float(raw_peak) / float(raw_1550)
        ),
        "calibration_id": calibration.scale_id,
        "calibration_multiplier": calibration.multiplier,
        "calibration_status": calibration.status,
        "raw_units": RAW_UNITS,
        "calibrated_units": CALIBRATED_UNITS,
    }


# ---------------------------------------------------------------------------
# Rendering -- Demo 16E's representations, Demo 17's deck
# ---------------------------------------------------------------------------


def template_path(cfg: Mapping[str, Any]) -> Path:
    """Where the deck template actually resolves to.

    The config names Demo 17's template by a relative path, so this is where the
    "same deck as Demo 17" claim either holds or does not. Resolved rather than
    joined so preflight can compare it to Demo 17's own directory.
    """

    return (DEMO_DIR / str(cfg["nextnano"]["template"])).resolve()


def render_deck(
    cfg: Mapping[str, Any],
    geometry: demo14.Geometry,
    profile: grading14.CompositionProfile,
    blocks: Mapping[str, str],
) -> str:
    """Fill Demo 17's template.

    A near-copy of ``demo17.render_deck``, and it exists for exactly the reason
    that one exists: ``demo17.render_deck`` resolves the template against **Demo
    17's** directory, so it cannot load a path written relative to this one. The
    substitutions are otherwise identical, which is what keeps the two decks
    comparable, and :func:`template_path` points at Demo 17's actual file so the
    grammar cannot drift even by accident.
    """

    path = template_path(cfg)
    if not path.is_file():
        raise Demo17EError(
            f"deck template not found: {path}. Demo 17E renders through Demo 17's "
            "validated template by reference; a missing file means the demo tree "
            "was moved or split."
        )
    text = path.read_text(encoding="utf-8")
    mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    outer = float(cfg["mesh"]["outer_grid_spacing_nm"])
    lo, hi = geometry.domain_nm
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    grid_lines = "\n".join([
        f"        line{{ pos = {lo:.6f}  spacing = {outer:.6f} }}",
        f"        line{{ pos = {geometry.active_start_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {geometry.active_end_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {hi:.6f}  spacing = {outer:.6f} }}",
    ])
    substitutions = {
        "temperature_K": cfg["materials"]["temperature_K"],
        "import_block": blocks["import_block"],
        "grid_lines": grid_lines,
        "structure_regions": demo14._structure_regions(cfg, geometry, blocks),
        "quantum_region_name": cfg["nextnano"]["quantum_region_name"],
        "quantum_start_nm": f"{max(lo, geometry.active_start_nm - padding):.6f}",
        "quantum_end_nm": f"{min(hi, geometry.active_end_nm + padding):.6f}",
        "number_of_electron_states": cfg["states"]["number_of_electron_states"],
        "number_of_hole_states": cfg["states"]["number_of_hole_states"],
        "output_state_count": cfg["states"]["output_state_count"],
        "dipole_polarization_name": cfg["nextnano"]["dipole_polarization_name"],
    }
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", str(value))
    if "{{" in text or "}}" in text:
        raise Demo17EError(f"{path.name} still contains unsubstituted placeholders.")
    return text


def build_case(cfg: Mapping[str, Any], case: cases17e.GradingCase):
    """Demo 14 geometry and profile, Demo 16E rendering, Demo 17 deck.

    ``demo16e.render_blocks`` is reused deliberately: the abrupt reference has to
    be rendered exactly the way Demo 17 rendered its own abrupt case, or the
    anchor the 20 realizations are measured against is not the anchor Demo 17
    solved.
    """

    parameters = case.parameters()
    geometry = demo14.geometry_for(cfg, parameters)
    profile = demo14.build_grading(cfg, parameters, geometry)
    blocks = demo16e.render_blocks(case, profile)
    deck = render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def quantum_region_nm(
    cfg: Mapping[str, Any], geometry: demo14.Geometry
) -> tuple[float, float]:
    """The span the Dirichlet walls will actually sit at, after clamping."""

    lo, hi = geometry.domain_nm
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    return (
        max(lo, geometry.active_start_nm - padding),
        min(hi, geometry.active_end_nm + padding),
    )


def deck_geometry_record(
    cfg: Mapping[str, Any], case: cases17e.GradingCase
) -> dict[str, Any]:
    """What correction C did to this case's deck, in numbers."""

    geometry, _profile, _blocks, _deck = build_case(cfg, case)
    start, end = quantum_region_nm(cfg, geometry)
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    return {
        "case_id": case.case_id,
        "domain_nm": list(geometry.domain_nm),
        "domain_width_nm": geometry.domain_nm[1] - geometry.domain_nm[0],
        "active_region_nm": [geometry.active_start_nm, geometry.active_end_nm],
        "active_region_width_nm": geometry.active_end_nm - geometry.active_start_nm,
        "quantum_region_nm": [start, end],
        "quantum_region_width_nm": end - start,
        "dirichlet_clearance_left_nm": geometry.active_start_nm - start,
        "dirichlet_clearance_right_nm": end - geometry.active_end_nm,
        "quantum_region_clamped_by_domain": bool(
            start > geometry.active_start_nm - padding + 1e-9
            or end < geometry.active_end_nm + padding - 1e-9
        ),
    }


# ---------------------------------------------------------------------------
# Licensed full physics -- Demo 16E's gates, Demo 17E's decks
# ---------------------------------------------------------------------------


def physics_raw_output_dir(case_dir: Path, case: cases17e.GradingCase) -> Path:
    return demo16e.physics_raw_output_dir(case_dir, case)


def full_physics_command(
    cfg: Mapping[str, Any], case: cases17e.GradingCase, case_dir: Path, *, machine: Any
) -> list[str]:
    return demo16e.full_physics_command(cfg, case, case_dir, machine=machine)


def run_case(
    cfg: Mapping[str, Any], case: cases17e.GradingCase, case_dir: Path,
    *, exe: Path | None, database: Path | None, license_path: Path | None = None,
    do_parse: bool = True, do_structure: bool = False,
) -> demo16e.CaseOutcome:
    """Demo 16E's render/parse/structure ladder driven by Demo 17E's builder."""

    return demo16e.run_case(
        cfg, case, case_dir, exe=exe, database=database,
        license_path=license_path, do_parse=do_parse, do_structure=do_structure,
        build=build_case,
    )


def solve_case(
    cfg: Mapping[str, Any], case: cases17e.GradingCase, case_dir: Path, *, machine: Any
) -> dict[str, Any]:
    """Demo 16B's gated full solve, driven by Demo 17E's renderer."""

    raw_output = physics_raw_output_dir(case_dir, case)
    record = demo16b.solve_case(
        cfg, case, case_dir, machine=machine, raw_output_dir=raw_output,
        build=build_case,
    )
    if not record.get("passed"):
        record.setdefault("diagnostics", {})["raw_output_dir"] = str(raw_output)
        runlog14.write_json_atomic(
            Path(case_dir) / "physics" / "physics_result.json", record
        )
    return record


def localization(cfg: Mapping[str, Any], raw: Path, profile):
    return demo16e.localization(cfg, raw, profile)


def write_wavefunction_csv(path: Path, waves) -> Path:
    return demo16e.write_wavefunction_csv(path, waves)


# ---------------------------------------------------------------------------
# Per-case optical artifacts
# ---------------------------------------------------------------------------


def verify_production_settings(parsed: Path) -> dict[str, Any]:
    """The corrections must be in force in the settings THIS case was evaluated with.

    Demo 17 measured corrections A and B once, by ablation, and 17E does not
    repeat that: re-measuring one convention against itself on 21 realizations
    adds no information. What does have to hold per case is that the conventions
    reached the evaluator at all, so the settings object the production analysis
    actually wrote is read back and checked against values computed here from
    first principles -- 2 wells / 30 nm, and 0.10 * 2*pi/a -- rather than against
    a constant copied out of the config.
    """

    path = Path(parsed) / "chi2_settings.json"
    if not path.is_file():
        raise Demo17EError(
            f"{path} was not written, so which conventions this case was "
            "evaluated under cannot be established."
        )
    settings = json.loads(path.read_text(encoding="utf-8"))
    n_z = settings.get("n_wells_per_metre")
    k_max = settings.get("k_max_per_nm")
    if n_z is None or not math.isclose(float(n_z), EXPECTED_N_Z_PER_M, rel_tol=1e-9):
        raise Demo17EError(
            f"correction A did not reach the evaluator: N_z = {n_z} m^-1 against "
            f"the {EXPECTED_N_Z_PER_M:.6e} m^-1 that 2 wells per 30 nm require."
        )
    if k_max is None or not math.isclose(
        float(k_max), EXPECTED_K_MAX_PER_NM, rel_tol=1e-9
    ):
        raise Demo17EError(
            f"correction B did not reach the evaluator: k_max = {k_max} nm^-1 "
            f"against the {EXPECTED_K_MAX_PER_NM:.6f} nm^-1 that 0.10 of the "
            "zincblende 2*pi/a edge requires."
        )
    if str(settings.get("mode")) != "absolute":
        raise Demo17EError(
            f"this case was evaluated in {settings.get('mode')!r} mode; Demo 17E "
            "reports pm/V and needs absolute mode."
        )
    return {
        "settings_path": str(path),
        "n_wells_per_metre": float(n_z),
        "k_max_per_nm": float(k_max),
        "broadening_meV": settings.get("broadening_meV"),
        "max_states_per_band": settings.get("max_states_per_band"),
        "r_e_hh_nm": settings.get("r_e_hh_nm"),
        "correction_A_in_force": True,
        "correction_B_in_force": True,
    }


def augment_matrix_elements(
    parsed: Path, metrics: Mapping[str, Any], calibration: CalibrationScale
) -> Path:
    """Add the named Eq. 2 scalars to the matrices Demo 11 already wrote.

    ``matrix_elements.json`` is a production artifact: Demo 11 writes the three
    2x2 matrices into it, and Demo 17b/17d read them from there. It is merged
    rather than replaced, so the file at the path Demo 17E advertises carries
    strictly more than before and nothing that was there is lost -- the raw
    matrices stay exactly as the solver's analysis produced them, and the named
    scalars, the state energies and the reporting scale are added beside them.
    """

    path = Path(parsed) / "matrix_elements.json"
    payload: dict[str, Any] = {}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Demo17EError(f"{path} is not readable JSON: {exc}") from exc
    else:
        raise Demo17EError(
            f"{path} was not written by the production analysis; Eq. 2's inputs "
            "for this case cannot be recorded."
        )
    named = {key: metrics.get(key) for key in MATRIX_ELEMENT_KEYS}
    missing = [key for key, value in named.items() if value is None]
    payload.update({
        "demo17e_version": DEMO_VERSION,
        "augmented_by": "demo17e.augment_matrix_elements",
        "named_elements": named,
        "named_elements_missing": missing,
        "electron_energies_eV": metrics.get("electron_energies_eV"),
        "heavy_hole_energies_eV": metrics.get("heavy_hole_energies_eV"),
        "state_labels": list(STATE_LABELS),
        "orthonormality_error_electron": metrics.get("orthonormality_error_electron"),
        "orthonormality_error_heavy_hole": metrics.get("orthonormality_error_heavy_hole"),
        "reporting_scale": calibration.as_record(),
        "note": (
            "position matrix elements are in nm on the solver's own z origin, "
            "which sits at the domain edge; Eq. 2's conduction and valence terms "
            "cancel that offset exactly, so the large diagonal values are "
            "expected and are not an error"
        ),
    })
    return runlog14.write_json_atomic(path, payload)


def paper_comparison(
    cfg: Mapping[str, Any], case: cases17e.GradingCase,
    optical: Mapping[str, Any], calibration: CalibrationScale,
) -> dict[str, Any] | None:
    """The abrupt reference against the paper's stated 2340 pm/V.

    Returns ``None`` for the 20 realizations: the paper states no absolute value
    for a randomly graded interface, and inventing a comparison would be worse
    than having none. The realizations are compared to the SOLVED abrupt anchor
    instead, which is what :func:`master_row`'s ``*_vs_reference`` columns carry.
    """

    if not case.is_paper_target:
        return None
    reference = cfg["paper_reference"]
    target = float(reference["expectations"]["chi2_ideal_abrupt_pm_per_V"])
    resonance_target = float(reference["expectations"]["simulated_resonance_nm"])
    low, high = (float(v) for v in reference["plausibility_band_pm_per_V"])
    raw = optical.get("chi2_at_1550")
    peak_raw = optical.get("spectral_peak_chi2")
    peak_nm = optical.get("spectral_peak_wavelength_nm")
    if raw is None:
        return {
            "case_id": case.case_id, "target_pm_per_V": target,
            "computed_raw_pm_per_V": None, "comparable": False,
            "reason": "the optical analysis produced no value",
        }
    raw = float(raw)
    return {
        "case_id": case.case_id,
        "structure": "ideal abrupt 7.1 / 1.8 / 2.9 nm, s = 0.42",
        "target_pm_per_V": target,
        "target_source": "arXiv:2602.23246v1 Section 3.1, stated in words",
        "target_quantity": "spectral peak of the ideal abrupt structure",
        "computed_raw_pm_per_V": raw,
        "computed_raw_peak_pm_per_V": peak_raw,
        "computed_calibrated_pm_per_V": calibration.apply(raw),
        "computed_calibrated_peak_pm_per_V": calibration.apply(peak_raw),
        "comparable": True,
        # Reported against the RAW value: the residual is the thing a prefactor
        # argument is trying to explain, so dividing it out first would hide it.
        "remaining_factor_on_raw_peak": (
            None if not peak_raw else target / float(peak_raw)
        ),
        "remaining_factor_on_calibrated_peak": (
            None if not peak_raw
            else target / float(calibration.apply(peak_raw) or math.inf)
        ),
        "within_plausibility_band_raw": bool(low <= raw <= high),
        "plausibility_band_pm_per_V": [low, high],
        "resonance_target_nm": resonance_target,
        "resonance_computed_nm": peak_nm,
        "resonance_error_nm": (
            None if peak_nm is None else float(peak_nm) - resonance_target
        ),
        "interpretation": (
            "The resonance position is the part of the reproduction no prefactor "
            "can move, so it is reported beside the amplitude rather than under "
            "it. A remaining factor is reported, never applied."
        ),
        "calibration": calibration.as_record(),
    }


def analyse_optics(
    cfg: Mapping[str, Any], case: cases17e.GradingCase, case_dir: Path,
    raw_output: Path, *, calibration: CalibrationScale,
) -> dict[str, Any]:
    """Demo 11/14's absolute chi(2) on this case's states, raw and calibrated.

    The spectrum itself is the production one, evaluated exactly as Demo 17
    evaluates it -- the settings are Demo 17's, verified per case by
    :func:`verify_production_settings`. The 1550 nm value is interpolated from
    that spectrum and cross-checked against the production evaluation of the same
    quantity, because the curve and the number in the table disagreeing would
    mean they came from different calculations.
    """

    geometry, profile, _blocks, _deck = build_case(cfg, case)
    optical_root = Path(case_dir) / "physics" / "optical"
    parsed = optical_root / "parsed"
    plots_dir = optical_root / "plots"
    parsed.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    metrics = demo14.analyse_real_trial(
        cfg,
        {"nextnano_output": Path(raw_output), "parsed": parsed, "plots": plots_dir},
        geometry,
        profile,
    )
    settings_check = verify_production_settings(parsed)

    spectrum_path = parsed / "chi2_focused.csv"
    if not spectrum_path.is_file():
        raise Demo17EError(f"production optical analysis did not write {spectrum_path}")
    spectrum = np.loadtxt(spectrum_path, delimiter=",", skiprows=1)
    wavelength = np.asarray(spectrum[:, 0], dtype=float)
    magnitude = np.asarray(spectrum[:, 3], dtype=float)
    grid = wavelength_grid(cfg)
    if wavelength.size != grid.size or not np.allclose(wavelength, grid, atol=1e-9):
        raise Demo17EError(
            f"{case.case_id} was evaluated on a {wavelength.size}-point grid from "
            f"{wavelength[0]:.1f} to {wavelength[-1]:.1f} nm, not the "
            f"{grid.size}-point 1 nm grid every other case uses; the spectra "
            "cannot be compared point by point."
        )
    chi2_1550 = float(np.interp(TARGET_WAVELENGTH_NM, wavelength, magnitude))
    peak_index = int(np.argmax(magnitude))
    peak_nm = float(wavelength[peak_index])
    peak_magnitude = float(magnitude[peak_index])
    production_value = metrics.get("chi2_relative_at_reference")
    if production_value is not None and not np.isclose(
        chi2_1550, float(production_value), rtol=1e-10, atol=1e-12
    ):
        raise Demo17EError(
            "1550 nm spectrum interpolation disagrees with production evaluation: "
            f"{chi2_1550} versus {production_value}"
        )
    if str(metrics.get("chi2_mode")) != "absolute" or "pm/V" not in str(
        metrics.get("chi2_units", "")
    ):
        raise Demo17EError(
            "Demo 17E reports pm/V and the analysis did not return absolute units: "
            f"mode={metrics.get('chi2_mode')!r}, units={metrics.get('chi2_units')!r}."
        )

    envelopes_path = parsed / "envelopes.csv"
    if not envelopes_path.is_file():
        raise Demo17EError(
            f"{envelopes_path} was not written; Eq. 2's signed amplitudes for this "
            "case cannot be archived or re-checked."
        )
    matrix_path = augment_matrix_elements(parsed, metrics, calibration)

    base = {
        "chi2_at_1550": chi2_1550,
        "spectral_peak_chi2": peak_magnitude,
        "spectral_peak_wavelength_nm": peak_nm,
        "detuning_from_1550_nm": peak_nm - TARGET_WAVELENGTH_NM,
    }
    result = {
        "passed": True,
        "case_id": case.case_id,
        "demo17e_version": DEMO_VERSION,
        "target_wavelength_nm": TARGET_WAVELENGTH_NM,
        **base,
        "chi2_units": metrics.get("chi2_units"),
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "scan_window_nm": [float(wavelength[0]), float(wavelength[-1])],
        "scan_points": int(wavelength.size),
        "scales": scaled_optics(base, calibration),
        "corrections_in_force": settings_check,
        "spectrum_path": str(spectrum_path),
        "envelopes_path": str(envelopes_path),
        "matrix_elements_path": str(matrix_path),
        "analysis_settings_path": str(parsed / "chi2_settings.json"),
        "selected_states_path": str(parsed / "state_count_audit.json"),
        # Demo 17's strict per-state verdict, applied over the states inside
        # Eq. 2's window. Tri-state: None means the question was not answered
        # and no caller may read that as success.
        "bound_state_verdict": demo17.bound_state_verdict(parsed),
        "deck_geometry": deck_geometry_record(cfg, case),
        "paper_comparison": paper_comparison(cfg, case, base, calibration),
        "production_metrics": metrics,
    }
    runlog14.write_json_atomic(optical_root / "optical_result.json", result)
    return result


def read_spectrum(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """``(wavelength_nm, |chi2|)`` from a production ``chi2_focused.csv``."""

    path = Path(path)
    if not path.is_file():
        return None
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 4:
        return None
    return np.asarray(data[:, 0], dtype=float), np.asarray(data[:, 3], dtype=float)


# ---------------------------------------------------------------------------
# Cross-case comparison
# ---------------------------------------------------------------------------


derived_energies = demo16e.derived_energies
energy_shifts = demo16e.energy_shifts
overlap_geometry = demo16e.overlap_geometry
render_method = demo16e.render_method
representation_of = demo16e.representation_of


def master_row(
    case: cases17e.GradingCase, record: Mapping[str, Any],
    comparison: Mapping[str, Any], representation: str,
    calibration: CalibrationScale,
) -> dict[str, Any]:
    """One row of the study summary, in Demo 17E's own field names.

    Built on Demo 16E's row so a 17E table and a 16E table still line up column
    for column where they overlap, then extended with the three things this demo
    exists to report: the sampled interface widths, the dual scale, and the
    bound-state verdict for the states Eq. 2 actually used.
    """

    row = dict(demo16e.master_row(case, record, comparison, representation))
    optical = record.get("optical") or {}
    scales = optical.get("scales") or scaled_optics(optical, calibration)
    verdict = optical.get("bound_state_verdict") or {}
    geometry = optical.get("deck_geometry") or {}
    paper = optical.get("paper_comparison") or {}
    boundary = [
        state.get("boundary_probability") for state in verdict.get("states") or []
        if state.get("boundary_probability") is not None
    ]
    sampled = dict(case.sampled_widths_nm)
    row.update({
        "case_name": case.name,
        "realization_index": case.realization_index,
        "is_reference_case": case.is_reference,
        "is_paper_target_case": case.is_paper_target,
        "severity": case.severity,
        # --- what was drawn, and what was rendered ------------------------
        "sigma_gaas_to_algaas_barrier_nm": sampled.get("gaas_to_algaas_barrier"),
        "sigma_algaas_to_gaas_well_nm": sampled.get("algaas_to_gaas_well"),
        "sigma_gaas_to_algaas_cladding_nm": sampled.get("gaas_to_algaas_cladding"),
        "deck_rise_grading_nm": float(case.left_grading_width_nm),
        "deck_fall_grading_nm": float(case.right_grading_width_nm),
        "mean_grading_width_nm": case.mean_interface_width_nm(),
        "rise_tie_residual_nm": case.rise_tie_residual_nm(),
        "narrowest_ramp_mesh_cells": (
            None if case.is_abrupt else case.ramp_cells()
        ),
        # --- the dual scale ------------------------------------------------
        **{key: value for key, value in scales.items()},
        # --- quality control -----------------------------------------------
        "bound_states_certified": verdict.get("certified"),
        "bound_states_failing": len(verdict.get("failing") or []),
        "max_boundary_probability": max(boundary) if boundary else None,
        "quantum_region_width_nm": geometry.get("quantum_region_width_nm"),
        "dirichlet_clearance_nm": geometry.get("dirichlet_clearance_left_nm"),
        "paper_target_pm_per_V": paper.get("target_pm_per_V"),
        "paper_remaining_factor_on_raw_peak": paper.get("remaining_factor_on_raw_peak"),
        "envelopes_csv_path": optical.get("envelopes_path"),
        "matrix_elements_path": optical.get("matrix_elements_path"),
    })
    return row


def add_reference_comparison(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Fill every row's shift and ratio against the solved abrupt reference.

    Ratios are taken on the RAW column only. A calibrated ratio would be
    identical -- one multiplier divided by itself -- so computing it would
    suggest the calibration told us something about the trend, and it did not.
    """

    rows = [dict(row) for row in rows]
    reference = next(
        (row for row in rows if row.get("case") == cases17e.REFERENCE_CASE_ID), None
    )
    for row in rows:
        if reference is None:
            row.update({
                **{f"delta_{label}_meV_vs_reference": None for label in STATE_LABELS},
                "chi2_1550_over_reference": None,
                "peak_chi2_over_reference": None,
                "chi2_1550_change_percent_vs_reference": None,
                "peak_wavelength_shift_nm_vs_reference": None,
                "reference_case": None,
            })
            continue
        row.update(energy_shifts(row, reference))
        ratio_1550 = _ratio(
            row.get("chi2_1550_raw_pm_per_V"),
            reference.get("chi2_1550_raw_pm_per_V"),
        )
        row.update({
            "chi2_1550_over_reference": ratio_1550,
            "peak_chi2_over_reference": _ratio(
                row.get("peak_chi2_raw_pm_per_V"),
                reference.get("peak_chi2_raw_pm_per_V"),
            ),
            "chi2_1550_change_percent_vs_reference": (
                None if ratio_1550 is None else (ratio_1550 - 1.0) * 100.0
            ),
            "peak_wavelength_shift_nm_vs_reference": _difference(
                row.get("peak_wavelength_nm"), reference.get("peak_wavelength_nm")
            ),
            "reference_case": cases17e.REFERENCE_CASE_ID,
        })
    return rows


def _ratio(value: Any, reference: Any) -> float | None:
    if value is None or not reference:
        return None
    return float(value) / float(reference)


def _difference(value: Any, reference: Any) -> float | None:
    if value is None or reference is None:
        return None
    return float(value) - float(reference)


def _finite(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    return [
        float(row[key]) for row in rows
        if row.get(key) is not None and np.isfinite(float(row[key]))
    ]


def _describe(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "median": None,
                "max": None, "stdev": None, "relative_stdev": None}
    mean = pystats.fmean(values)
    stdev = pystats.stdev(values) if len(values) > 1 else 0.0
    return {
        "count": len(values),
        "min": min(values),
        "mean": mean,
        "median": pystats.median(values),
        "max": max(values),
        "stdev": stdev,
        "relative_stdev": (stdev / abs(mean)) if mean else None,
    }


def grading_trend(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    """Least-squares slope of one quantity against mean interface width.

    Descriptive, and only over the 20 graded realizations -- the abrupt reference
    is a different kind of structure (no ramps in its deck at all), so including
    it would let one point at x = 0 lever the whole line.

    A straight line is not claimed to be the right model for chi(2) against
    roughness; it is the simplest summary of a monotone trend and is reported
    with its correlation so a reader can see how well it describes the cloud.
    """

    pairs = [
        (float(row["mean_grading_width_nm"]), float(row[key]))
        for row in rows
        if not row.get("is_reference_case")
        and row.get("mean_grading_width_nm") is not None
        and row.get(key) is not None
        and np.isfinite(float(row[key]))
    ]
    if len(pairs) < 3:
        return {"quantity": key, "points": len(pairs), "computable": False,
                "reason": "fewer than three realizations carry this quantity"}
    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual_ss = float(np.sum((y - predicted) ** 2))
    total_ss = float(np.sum((y - y.mean()) ** 2))
    correlation = (
        float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None
    )
    return {
        "quantity": key,
        "points": len(pairs),
        "computable": True,
        "x": "mean interface grading width (nm), as rendered",
        "slope_per_nm": float(slope),
        "intercept": float(intercept),
        "r_squared": (None if total_ss == 0 else 1.0 - residual_ss / total_ss),
        "pearson_r": correlation,
        "value_at_min_width": float(slope * x.min() + intercept),
        "value_at_max_width": float(slope * x.max() + intercept),
        "width_span_nm": [float(x.min()), float(x.max())],
        "model_note": (
            "a straight line is the simplest summary of a monotone trend, not a "
            "claim about the functional form; r^2 says how well it describes the "
            "20 realizations"
        ),
    }


def roughness_statistics(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """What the 20 realizations did to chi(2), against the abrupt anchor.

    The headline of the whole demo. Reported on the raw column, per severity
    band and over the ensemble, with the reference kept separate throughout: it
    is the anchor, not a sample, and averaging it into the ensemble would drag
    every statistic toward a structure that was never drawn.
    """

    bands = (cfg or {}).get("severity_bands") or cases17e.DEFAULT_SEVERITY_BANDS
    reference = next((row for row in rows if row.get("is_reference_case")), None)
    graded = [row for row in rows if not row.get("is_reference_case")]

    per_band: dict[str, Any] = {}
    for band in bands:
        key = str(band["key"])
        members = [row for row in graded if row.get("severity") == key]
        per_band[key] = {
            "label": str(band.get("label", key)),
            "cases": [row.get("case") for row in members],
            "count": len(members),
            "mean_grading_width_nm": _describe(
                _finite(members, "mean_grading_width_nm")
            ),
            "chi2_1550_raw_pm_per_V": _describe(
                _finite(members, "chi2_1550_raw_pm_per_V")
            ),
            "peak_chi2_raw_pm_per_V": _describe(
                _finite(members, "peak_chi2_raw_pm_per_V")
            ),
            "peak_wavelength_nm": _describe(_finite(members, "peak_wavelength_nm")),
            "chi2_1550_over_reference": _describe(
                _finite(members, "chi2_1550_over_reference")
            ),
        }

    certified = [row.get("bound_states_certified") for row in rows]
    return {
        "cases_reported": len(rows),
        "realizations_reported": len(graded),
        "reference_case": cases17e.REFERENCE_CASE_ID,
        "reference": None if reference is None else {
            "chi2_1550_raw_pm_per_V": reference.get("chi2_1550_raw_pm_per_V"),
            "peak_chi2_raw_pm_per_V": reference.get("peak_chi2_raw_pm_per_V"),
            "peak_wavelength_nm": reference.get("peak_wavelength_nm"),
            "note": "ideal abrupt interfaces; the anchor, not a sample",
        },
        "ensemble": {
            "mean_grading_width_nm": _describe(
                _finite(graded, "mean_grading_width_nm")
            ),
            "chi2_1550_raw_pm_per_V": _describe(
                _finite(graded, "chi2_1550_raw_pm_per_V")
            ),
            "peak_chi2_raw_pm_per_V": _describe(
                _finite(graded, "peak_chi2_raw_pm_per_V")
            ),
            "peak_wavelength_nm": _describe(_finite(graded, "peak_wavelength_nm")),
            "chi2_1550_over_reference": _describe(
                _finite(graded, "chi2_1550_over_reference")
            ),
            "peak_chi2_over_reference": _describe(
                _finite(graded, "peak_chi2_over_reference")
            ),
        },
        "by_severity": per_band,
        "trends": {
            "chi2_at_1550": grading_trend(rows, "chi2_1550_raw_pm_per_V"),
            "peak_chi2": grading_trend(rows, "peak_chi2_raw_pm_per_V"),
            "peak_wavelength": grading_trend(rows, "peak_wavelength_nm"),
        },
        "bound_states_certified": {
            "true": sum(1 for value in certified if value is True),
            "false": sum(1 for value in certified if value is False),
            "not_certified": sum(1 for value in certified if value is None),
        },
        "statistics_are_on_the_raw_column": True,
        "why_raw": (
            "every scale in this demo's calibrated column is one global "
            "multiplier, and a global multiplier cannot change a ratio, a slope's "
            "sign or a relative spread. Reporting the statistics on the raw "
            "column keeps them free of a declared factor they do not depend on."
        ),
    }


def study_summary(
    cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
    calibration: CalibrationScale, plan: cases17e.SamplingPlan,
) -> dict[str, Any]:
    """The one-paragraph answer: what interface roughness was worth."""

    target_row = next((row for row in rows if row.get("is_paper_target_case")), None)
    return {
        "demo_id": DEMO_ID,
        "demo17e_version": DEMO_VERSION,
        "structural_engine": demo16e.DEMO_VERSION,
        "correction_engine": demo17.DEMO_VERSION,
        "cases_reported": len(rows),
        "optimization_performed": False,
        "sampling": plan.as_record(),
        "corrections": demo17.corrections_record(cfg),
        "calibration": calibration_record(cfg, calibration),
        "roughness": roughness_statistics(rows, cfg),
        "paper_target": {
            "case_id": cases17e.PAPER_TARGET_CASE_ID,
            "target_pm_per_V": cases17e.PAPER_TARGET_PM_PER_V,
            "computed_raw_peak_pm_per_V": (
                None if target_row is None else target_row.get("peak_chi2_raw_pm_per_V")
            ),
            "computed_calibrated_peak_pm_per_V": (
                None if target_row is None
                else target_row.get("peak_chi2_calibrated_pm_per_V")
            ),
            "remaining_factor_on_raw_peak": (
                None if target_row is None
                else target_row.get("paper_remaining_factor_on_raw_peak")
            ),
        },
        "known_open_factors_not_applied": (
            cfg.get("corrections") or {}
        ).get("known_open_factors"),
        "no_scale_factor_was_fitted_in_the_raw_column": True,
    }


def spectrum_matrix(
    cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
    calibration: CalibrationScale,
) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Every case's spectrum on one grid: ``(wavelength, case_ids, magnitudes)``.

    ``magnitudes`` is ``(cases, points)`` in RAW pm/V. Cases whose spectrum is
    missing are left out of ``case_ids`` entirely rather than padded with zeros,
    so a shortened matrix is visibly short instead of quietly wrong.
    """

    grid = wavelength_grid(cfg)
    ids: list[str] = []
    stack: list[np.ndarray] = []
    for row in rows:
        spectrum = read_spectrum(row.get("spectrum_path") or "")
        if spectrum is None:
            continue
        wavelength, magnitude = spectrum
        if wavelength.size != grid.size or not np.allclose(wavelength, grid, atol=1e-9):
            raise Demo17EError(
                f"{row.get('case')} spectrum is not on the shared 1 nm grid; the "
                "all-case matrix would be misaligned."
            )
        ids.append(str(row.get("case")))
        stack.append(magnitude)
    if not stack:
        return grid, [], np.zeros((0, grid.size), dtype=float)
    return grid, ids, np.vstack(stack)


def write_spectrum_matrix(
    path: Path, cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
    calibration: CalibrationScale,
) -> Path | None:
    """``chi2_spectrum_all_cases.csv``: raw and calibrated, every case, one grid.

    Two columns per case rather than one, because a reader plotting this file
    should not have to know the multiplier to reproduce either figure, and a
    reader who only wants the physics should not have to divide it out.
    """

    grid, ids, magnitudes = spectrum_matrix(cfg, rows, calibration)
    if not ids:
        return None
    columns = ["wavelength_nm"]
    for case_id in ids:
        columns += [f"{case_id}_raw_pm_per_V", f"{case_id}_calibrated_pm_per_V"]
    multiplier = float(calibration.multiplier)
    lines = [
        "# Demo 17E chi(2) spectra, all cases, "
        f"{grid[0]:.0f}-{grid[-1]:.0f} nm at 1 nm.",
        f"# raw = Demo 17-corrected Eq. 2, no multiplier. calibrated = raw x "
        f"{multiplier:g} ({calibration.scale_id}, status: {calibration.status}).",
        "# " + CALIBRATION_WARNING.replace("\n", " "),
        ",".join(columns),
    ]
    for index, wavelength in enumerate(grid):
        values = [f"{wavelength:.4f}"]
        for row_index in range(len(ids)):
            raw = float(magnitudes[row_index, index])
            values += [f"{raw:.10g}", f"{raw * multiplier:.10g}"]
        lines.append(",".join(values))
    return runlog14.write_text_atomic(Path(path), "\n".join(lines) + "\n")


def write_manifests(
    root: Path, cfg: Mapping[str, Any], calibration: CalibrationScale
) -> None:
    """Stamp the corrections and the reporting scales before anything is solved.

    Written first so what a run claims cannot be edited into it afterwards.
    """

    demo17.write_corrections_manifest(Path(root) / "corrections_applied.yaml", cfg)
    runlog14.write_text_atomic(
        Path(root) / "reporting_scales.yaml",
        yaml.safe_dump(calibration_record(cfg, calibration), sort_keys=False,
                       default_flow_style=False),
    )
