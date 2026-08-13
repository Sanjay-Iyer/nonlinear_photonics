"""Demo 17 scientific core: Demo 16E's ten structures, three corrections applied.

Demo 17 changes the *calculation*, never the *structures*. The ten geometries,
the composition renderer, the parser gate, the realized-composition gate, the
solver invocation and the Eq. 2 evaluator are all Demo 16E's / Demo 14's /
Demo 11's, reused rather than reimplemented. What this module owns is exactly
the three corrections and the measurement that says how much each one was worth:

    A. N_z counts individual wells, not coupled pairs   x2, exactly
    B. Brillouin-zone edge is the zincblende 2*pi/a     measured
    C. the Dirichlet box is moved out of the way        measured

A and B are post-processing conventions: they can be switched on and off on ONE
set of solved wavefunctions, so :func:`correction_ablation` measures them
directly by re-evaluating Eq. 2 on the states this run produced. C is not -- it
changes the deck, so its effect only exists as a difference between two solves.
:func:`versus_baseline` measures it as Demo 17's states evaluated under Demo
16E's own settings, divided by the value Demo 16E recorded. That factorisation
is the whole point:

    chi2_17_corrected     chi2_17_legacy_settings      chi2_17_corrected
    ----------------- =   -----------------------  x  -----------------------
    chi2_16E_recorded     chi2_16E_recorded             chi2_17_legacy_settings
                                   |                            |
                                   C                          A x B

NOTHING HERE IS FITTED. There is no absolute_scale_factor, no free parameter and
no calibration. r_e_hh_nm, Gamma = 5 meV, the 0.10 zone fraction and the
two-states-per-band truncation are published values and all of them stay put;
only *which zone edge* the fraction is taken of changes, and that has a
crystallographic reason recorded beside it.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import cases17
import chi2 as chi2mod
import demo11
import demo14
import demo16b
import demo16e
import grading14
import physics14
import runlog14

DEMO_DIR = Path(__file__).resolve().parent
DEMO_ID = cases17.DEMO_ID
DEMO_VERSION = "demo17-1.0.0"
CONFIG_FILENAME = "demo.yaml"
TARGET_WAVELENGTH_NM = cases17.TARGET_WAVELENGTH_NM

#: Conventions and labels reused verbatim, so a Demo 17 table and a Demo 16E
#: table mean the same thing column for column.
STATE_LABELS = demo16e.STATE_LABELS
REGION_LABELS = demo16e.REGION_LABELS
LOCALIZATION_CONVENTION = demo16e.LOCALIZATION_CONVENTION
HOLE_ENERGY_CONVENTION = demo16e.HOLE_ENERGY_CONVENTION

#: The zone-edge numerator for each convention, in units of 1/a. ``chi2.py``
#: hardcodes the ``pi/a`` one, which is why correction B has to be expressed as
#: a fraction of it -- see :func:`verify_k_space_convention`.
LEGACY_ZONE_EDGE = math.pi
CORRECTED_ZONE_EDGE = 2.0 * math.pi

#: Where a repo-local Demo 16E baseline lives when one has been committed.
DEFAULT_BASELINE_SUMMARY = (
    DEMO_DIR.parents[2] / "demo_results" / "demo_16E" / "physics_summary.json"
)


class Demo17Error(RuntimeError):
    """A Demo 17 construction that is wrong rather than merely unusual."""


# ---------------------------------------------------------------------------
# Configuration and the three corrections
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Demo 17's own ``demo.yaml``, held to Demo 14's schema.

    ``demo14.validate_config`` is deliberately reused rather than relaxed: Demo
    17 changes three values inside that schema, so it should have to satisfy the
    same checks. The corrections are then verified on top, because the base
    schema has no opinion about which zone edge or which N_z is correct.
    """

    cfg = demo14.load_config(Path(path) if path else DEMO_DIR / CONFIG_FILENAME)
    warnings = list(demo14.validate_config(cfg))
    if "corrections" not in cfg:
        raise Demo17Error(
            "demo.yaml has no 'corrections' section; Demo 17 exists to apply "
            "three named corrections and must record which ones it applied."
        )
    for verify in (
        verify_nz_convention, verify_k_space_convention, verify_domain_convention
    ):
        verify(cfg)
    cfg.setdefault("_warnings", warnings)
    return cfg


def verify_nz_convention(cfg: Mapping[str, Any]) -> float:
    """Correction A: N_z must be the per-WELL density, and must be derived.

    Returns N_z in m^-1. Raises if the config asks for the old per-period
    counting, or if a hand-typed ``n_wells_per_metre`` disagrees with what the
    period and the well count actually give -- typing the number twice is how
    the two silently drift apart.
    """

    metric = cfg["chi2"]
    mode = str(metric.get("nz_mode"))
    if mode != "well_density":
        raise Demo17Error(
            f"correction A requires chi2.nz_mode = 'well_density', got {mode!r}. "
            "Ramesh 2023 Eq. 1 counts quantum wells per unit length, and Fig. 1a "
            "of arXiv:2602.23246v1 puts two GaAs wells in each 30 nm period."
        )
    period = float(metric["reference_period_nm"])
    wells = int(metric.get("wells_per_period", 2))
    derived = physics14.n_z_for(mode, period, wells)
    declared = metric.get("n_wells_per_metre")
    if declared is not None and not math.isclose(
        float(declared), derived, rel_tol=1e-9
    ):
        raise Demo17Error(
            f"chi2.n_wells_per_metre is {declared} but {wells} wells per "
            f"{period} nm period give {derived:.6e} m^-1. Leave it null so it is "
            "derived once instead of typed twice."
        )
    expected = wells / (period * 1.0e-9)
    if not math.isclose(derived, expected, rel_tol=1e-12):  # pragma: no cover
        raise Demo17Error(f"N_z derivation disagrees with {wells}/{period} nm.")
    return derived


def verify_k_space_convention(cfg: Mapping[str, Any]) -> float:
    """Correction B: the in-plane cutoff must be 0.10 of the ZINCBLENDE edge.

    ``chi2.Chi2Settings.k_max_per_nm`` hardcodes ``pi/a``. That module is shared
    with Demos 11, 13, 14 and 16B-16E, and Demo 17 does not get to move their
    results, so the physically correct radius is requested through the only knob
    that reaches it -- the fraction:

        fraction_of_bz * (pi/a)  ==  physical_fraction * (2*pi/a)

    which means ``fraction_of_bz`` must be exactly twice the physical fraction.
    This function is the guard on that identity. Without it, `fraction_of_bz:
    0.20` in the YAML is indistinguishable from somebody having decided to
    integrate to a fifth of the zone, and the two mean very different things.

    Returns k_max in nm^-1.
    """

    kpar = cfg["k_parallel"]
    convention = str(kpar.get("zone_edge_convention"))
    if convention != "crystallographic_two_pi_over_a":
        raise Demo17Error(
            "correction B requires k_parallel.zone_edge_convention = "
            f"'crystallographic_two_pi_over_a', got {convention!r}. GaAs is "
            "zincblende (FCC): X = (1,0,0) in units of 2*pi/a, so the zone edge "
            "is 2*pi/a. pi/a is the simple-cubic edge."
        )
    if convention not in physics14.BZ_EDGE_CONVENTIONS:  # pragma: no cover
        raise Demo17Error(f"unknown zone-edge convention {convention!r}.")

    physical = float(kpar["fraction_of_brillouin_zone_physical"])
    effective = float(kpar["fraction_of_bz"])
    a_nm = float(kpar["lattice_constant_nm"])
    if not math.isclose(
        effective * LEGACY_ZONE_EDGE, physical * CORRECTED_ZONE_EDGE, rel_tol=1e-12
    ):
        raise Demo17Error(
            f"k_parallel.fraction_of_bz ({effective}) does not encode "
            f"{physical} of the 2*pi/a zone edge against chi2.py's pi/a "
            f"convention; it would have to be {physical * 2.0}. The YAML and the "
            "physics have drifted apart."
        )
    k_max = physical * CORRECTED_ZONE_EDGE / a_nm
    declared = kpar.get("target_k_max_per_nm")
    if declared is not None and not math.isclose(
        float(declared), k_max, rel_tol=1e-6
    ):
        raise Demo17Error(
            f"k_parallel.target_k_max_per_nm is {declared} nm^-1 but "
            f"{physical} * 2*pi / {a_nm} nm gives {k_max:.6f} nm^-1."
        )
    # The settings object is what actually reaches Eq. 2, so check the number it
    # will produce rather than the number the YAML claims.
    produced = physics14.settings_from_config(cfg).k_max_per_nm
    if not math.isclose(produced, k_max, rel_tol=1e-12):
        raise Demo17Error(
            f"Chi2Settings will integrate to {produced:.6f} nm^-1, not the "
            f"{k_max:.6f} nm^-1 correction B requires."
        )
    return k_max


def verify_domain_convention(cfg: Mapping[str, Any]) -> dict[str, float]:
    """Correction C: the Dirichlet box must be well clear of the active region.

    Two independent things have to hold, and neither implies the other:

    * the quantum region must be padded far beyond the wells, because that
      padding is where ``boundary{ x = dirichlet }`` puts psi = 0;
    * the domain must be wider still, or the quantum box is clamped at the
      domain edge and the padding silently is not what the config says.
    """

    geometry = cfg["geometry"]
    domain = float(geometry["domain_padding_nm"])
    quantum = float(geometry["quantum_region_padding_nm"])
    baseline = (cfg.get("corrections") or {}).get("applied") or []
    entry = next((row for row in baseline if row.get("id", "").startswith("C_")), None)
    if entry is None:
        raise Demo17Error("corrections.applied has no 'C_' entry to check against.")
    was_domain, was_quantum = (float(value) for value in entry["from"])
    if domain <= was_domain or quantum <= was_quantum:
        raise Demo17Error(
            f"correction C must widen the domain: got {domain}/{quantum} nm "
            f"against the {was_domain}/{was_quantum} nm baseline."
        )
    if quantum >= domain:
        raise Demo17Error(
            f"quantum_region_padding_nm ({quantum} nm) must stay inside "
            f"domain_padding_nm ({domain} nm), or the quantum box is clamped at "
            "the domain edge and the Dirichlet wall is not where it is declared."
        )
    # adapter14 reconstructs Demo 11's layer stack as
    # 0.5 * period_barrier + padding_11 == domain_padding, and refuses a
    # negative padding_11. Fail here, before a licensed solve, rather than there.
    half_period = 0.5 * float(geometry["period_barrier_nm"])
    if domain < half_period:
        raise Demo17Error(
            f"domain_padding_nm ({domain} nm) is below half the period barrier "
            f"({half_period} nm); Demo 11's layer stack cannot reproduce it."
        )
    return {
        "domain_padding_nm": domain,
        "quantum_region_padding_nm": quantum,
        "algaas_beyond_dirichlet_wall_nm": domain - quantum,
        "demo11_equivalent_padding_nm": domain - half_period,
    }


def chi2_settings(cfg: Mapping[str, Any]) -> chi2mod.Chi2Settings:
    """Demo 17's production settings: corrections A and B applied."""

    return physics14.settings_from_config(cfg)


def legacy_chi2_settings(cfg: Mapping[str, Any]) -> chi2mod.Chi2Settings:
    """Demo 16E's settings, for the ablation.

    Rebuilt from ``corrections.ablation`` rather than by importing Demo 14's
    config, so the ablation still runs in a bundle that shipped Demo 17 alone,
    and so the numbers being reversed are stated in one visible place.
    """

    ablation = (cfg.get("corrections") or {}).get("ablation") or {}
    if not ablation.get("enabled", False):
        raise Demo17Error("corrections.ablation is disabled; nothing to compare.")
    production = chi2_settings(cfg)
    period = float(cfg["chi2"]["reference_period_nm"])
    legacy_mode = str(ablation.get("legacy_nz_mode", "period_density"))
    return physics14.with_settings(
        production,
        n_wells_per_metre=physics14.n_z_for(
            legacy_mode, period, int(cfg["chi2"].get("wells_per_period", 2))
        ),
        k_parallel_fraction_of_bz=float(
            ablation.get("legacy_k_parallel_fraction_of_bz", 0.10)
        ),
        k_parallel_points=int(ablation.get("legacy_k_parallel_points", 96)),
    )


def corrections_record(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Everything about the three corrections, for stamping into artifacts."""

    production = chi2_settings(cfg)
    legacy = legacy_chi2_settings(cfg)
    return {
        "demo17_version": DEMO_VERSION,
        "baseline_demo_id": (cfg.get("corrections") or {}).get("baseline_demo_id"),
        "applied": (cfg.get("corrections") or {}).get("applied"),
        "known_open_factors": (cfg.get("corrections") or {}).get(
            "known_open_factors"
        ),
        "A_n_wells_per_metre": {
            "corrected": production.n_wells_per_metre,
            "legacy": legacy.n_wells_per_metre,
            "ratio": production.n_wells_per_metre / legacy.n_wells_per_metre,
        },
        "B_k_max_per_nm": {
            "corrected": production.k_max_per_nm,
            "legacy": legacy.k_max_per_nm,
            "ratio": production.k_max_per_nm / legacy.k_max_per_nm,
            "zone_edge_convention": cfg["k_parallel"]["zone_edge_convention"],
            "fraction_of_brillouin_zone_physical": cfg["k_parallel"][
                "fraction_of_brillouin_zone_physical"
            ],
            "fraction_of_bz_against_chi2py_pi_over_a": cfg["k_parallel"][
                "fraction_of_bz"
            ],
        },
        "C_domain": verify_domain_convention(cfg),
        "held_fixed": {
            "r_e_hh_nm": production.r_e_hh_nm,
            "broadening_meV": production.broadening_meV,
            "max_states_per_band": production.max_states_per_band,
            "spin_degeneracy": production.spin_degeneracy,
            "absolute_scale_factor": None,
        },
        "production_settings": production.as_record(),
        "legacy_settings": legacy.as_record(),
    }


# ---------------------------------------------------------------------------
# Rendering -- Demo 16E's three representations, Demo 17's template
# ---------------------------------------------------------------------------


def render_deck(
    cfg: Mapping[str, Any],
    geometry: demo14.Geometry,
    profile: grading14.CompositionProfile,
    blocks: Mapping[str, str],
) -> str:
    """Fill Demo 17's template.

    A near-copy of ``demo14.render_deck``, and it exists for one reason:
    ``demo14.render_deck`` resolves ``nextnano.template`` against **Demo 14's**
    directory, so it can never load ``graded_acqw17.in.j2``. The substitutions
    are otherwise identical, which is what keeps the two decks comparable.

    The correction-C numbers enter here, through ``geometry.domain_nm`` (which
    ``demo14.geometry_for`` already built from the wider ``domain_padding_nm``)
    and through the ``quantum_region_padding_nm`` read below.
    """

    template_path = DEMO_DIR / str(cfg["nextnano"]["template"])
    if not template_path.is_file():
        raise Demo17Error(f"Demo 17 template not found: {template_path}")
    text = template_path.read_text(encoding="utf-8")
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
    remaining = [
        token for token in ("{{", "}}") if token in text
    ]
    if remaining:
        raise Demo17Error(
            f"{template_path.name} still contains unsubstituted placeholders."
        )
    return text


def build_case(cfg: Mapping[str, Any], case: cases17.GeometryCase):
    """Demo 14 geometry and profile, Demo 16E rendering, Demo 17 deck.

    ``demo16e.render_blocks`` is reused deliberately: the abrupt, native-linear
    and imported representations are part of the structures Demo 17 is holding
    fixed, so reimplementing them here would be the one way to accidentally
    change them.
    """

    parameters = case.parameters()
    geometry = demo14.geometry_for(cfg, parameters)
    profile = demo14.build_grading(cfg, parameters, geometry)
    blocks = demo16e.render_blocks(case, profile)
    deck = render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def quantum_region_nm(cfg: Mapping[str, Any], geometry: demo14.Geometry) -> tuple[float, float]:
    """The span the Dirichlet walls will actually sit at, after clamping."""

    lo, hi = geometry.domain_nm
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    return (
        max(lo, geometry.active_start_nm - padding),
        min(hi, geometry.active_end_nm + padding),
    )


def deck_geometry_record(
    cfg: Mapping[str, Any], case: cases17.GeometryCase
) -> dict[str, Any]:
    """What correction C did to this case's deck, in numbers."""

    geometry, _profile, _blocks, _deck = build_case(cfg, case)
    start, end = quantum_region_nm(cfg, geometry)
    active = geometry.active_end_nm - geometry.active_start_nm
    return {
        "case_id": case.case_id,
        "domain_nm": list(geometry.domain_nm),
        "domain_width_nm": geometry.domain_nm[1] - geometry.domain_nm[0],
        "active_region_nm": [geometry.active_start_nm, geometry.active_end_nm],
        "active_region_width_nm": active,
        "quantum_region_nm": [start, end],
        "quantum_region_width_nm": end - start,
        "dirichlet_clearance_left_nm": geometry.active_start_nm - start,
        "dirichlet_clearance_right_nm": end - geometry.active_end_nm,
        "quantum_region_clamped_by_domain": bool(
            start > geometry.active_start_nm
            - float(cfg["geometry"]["quantum_region_padding_nm"]) + 1e-9
            or end < geometry.active_end_nm
            + float(cfg["geometry"]["quantum_region_padding_nm"]) - 1e-9
        ),
    }


# ---------------------------------------------------------------------------
# Licensed full physics -- Demo 16E's gates, Demo 17's deck
# ---------------------------------------------------------------------------


def physics_raw_output_dir(case_dir: Path, case: cases17.GeometryCase) -> Path:
    return demo16e.physics_raw_output_dir(case_dir, case)


def full_physics_command(
    cfg: Mapping[str, Any], case: cases17.GeometryCase, case_dir: Path, *, machine: Any
) -> list[str]:
    return demo16e.full_physics_command(cfg, case, case_dir, machine=machine)


def run_case(
    cfg: Mapping[str, Any], case: cases17.GeometryCase, case_dir: Path,
    *, exe: Path | None, database: Path | None, license_path: Path | None = None,
    do_parse: bool = True, do_structure: bool = False,
) -> demo16e.CaseOutcome:
    """Demo 16E's render/parse/structure ladder driven by Demo 17's builder."""

    return demo16e.run_case(
        cfg, case, case_dir, exe=exe, database=database,
        license_path=license_path, do_parse=do_parse, do_structure=do_structure,
        build=build_case,
    )


def solve_case(
    cfg: Mapping[str, Any], case: cases17.GeometryCase, case_dir: Path, *, machine: Any
) -> dict[str, Any]:
    """Demo 16B's gated full solve, driven by Demo 17's renderer."""

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


def localization(cfg: Mapping[str, Any], raw: Path, profile) -> tuple[dict[str, Any], Any]:
    return demo16e.localization(cfg, raw, profile)


def write_wavefunction_csv(path: Path, waves) -> Path:
    return demo16e.write_wavefunction_csv(path, waves)


# ---------------------------------------------------------------------------
# The correction ablation
# ---------------------------------------------------------------------------


def band_states_from_extracted(
    extracted: Path, metrics: Mapping[str, Any]
) -> tuple[chi2mod.BandStates, chi2mod.BandStates]:
    """Rebuild the two ``BandStates`` Eq. 2 was evaluated on.

    Read back from the artifacts the production analysis already wrote --
    ``envelopes.csv`` for the amplitudes and the observables for the energies --
    rather than re-parsing the raw solver tree. Re-parsing would introduce a
    second parser path, and then an ablation disagreement could mean either a
    real convention effect or two different readings of the same run.
    """

    path = Path(extracted) / "envelopes.csv"
    if not path.is_file():
        raise Demo17Error(f"the ablation needs {path}, which does not exist.")
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] != len(header):
        raise Demo17Error(f"{path} has {data.shape} values for {len(header)} columns.")
    z_nm = np.asarray(data[:, 0], dtype=float)
    e_columns = [i for i, name in enumerate(header) if name.startswith("psi_e")]
    h_columns = [i for i, name in enumerate(header) if name.startswith("psi_hh")]
    e_energies = np.asarray(metrics["electron_energies_eV"], dtype=float)
    h_energies = np.asarray(metrics["heavy_hole_energies_eV"], dtype=float)
    if len(e_columns) != e_energies.size or len(h_columns) != h_energies.size:
        raise Demo17Error(
            f"{path} has {len(e_columns)}/{len(h_columns)} envelope columns for "
            f"{e_energies.size}/{h_energies.size} energies; the artifacts "
            "disagree and the ablation would compare different states."
        )
    return (
        chi2mod.BandStates(z_nm, e_energies, data[:, e_columns], "e"),
        chi2mod.BandStates(z_nm, h_energies, data[:, h_columns], "hh"),
    )


@dataclass(frozen=True)
class AblationRung:
    """One convention set evaluated on one fixed pair of bands."""

    rung: str
    changed: str
    chi2_at_target_pm_per_V: float
    peak_wavelength_nm: float
    peak_pm_per_V: float
    n_wells_per_metre: float
    k_max_per_nm: float
    k_parallel_points: int

    def as_record(self) -> dict[str, Any]:
        return {
            "rung": self.rung,
            "changed": self.changed,
            "chi2_at_target_pm_per_V": self.chi2_at_target_pm_per_V,
            "peak_wavelength_nm": self.peak_wavelength_nm,
            "peak_pm_per_V": self.peak_pm_per_V,
            "n_wells_per_metre": self.n_wells_per_metre,
            "k_max_per_nm": self.k_max_per_nm,
            "k_parallel_points": self.k_parallel_points,
        }


def _evaluate(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    settings: chi2mod.Chi2Settings,
    grid_nm: np.ndarray,
    target_nm: float,
    *,
    rung: str,
    changed: str,
) -> AblationRung:
    spectrum = chi2mod.chi2_spectrum(
        electron, heavy_hole, chi2mod.photon_energy_eV(grid_nm), settings
    )
    peak = spectrum.peak()
    return AblationRung(
        rung=rung,
        changed=changed,
        chi2_at_target_pm_per_V=float(abs(spectrum.at_wavelength(target_nm))),
        peak_wavelength_nm=float(peak["wavelength_nm"]),
        peak_pm_per_V=float(peak["magnitude"]),
        n_wells_per_metre=float(settings.n_wells_per_metre),
        k_max_per_nm=float(settings.k_max_per_nm),
        k_parallel_points=int(settings.k_parallel_points),
    )


def correction_ablation(
    cfg: Mapping[str, Any], extracted: Path, metrics: Mapping[str, Any]
) -> dict[str, Any]:
    """Measure corrections A and B on THIS run's wavefunctions.

    A and B are post-processing conventions, so all three rungs below are the
    same solved states evaluated three ways -- no second solve, and no
    possibility that a structural difference leaks into the ratio. Correction C
    cannot appear here at all: it changed the deck, so it only exists as a
    difference between runs, and :func:`versus_baseline` is where it is measured.
    """

    electron, heavy_hole = band_states_from_extracted(extracted, metrics)
    focused = cfg["chi2"]["focused_wavelength_nm"]
    grid = np.linspace(
        float(focused[0]), float(focused[1]),
        int(cfg["chi2"]["focused_wavelength_points"]),
    )
    target = float(cfg["chi2"]["target_wavelength_nm"])
    production = chi2_settings(cfg)
    legacy = legacy_chi2_settings(cfg)
    only_a = physics14.with_settings(
        legacy, n_wells_per_metre=production.n_wells_per_metre
    )

    rungs = [
        _evaluate(electron, heavy_hole, legacy, grid, target,
                  rung="legacy",
                  changed="nothing; Demo 16E's conventions on Demo 17's states"),
        _evaluate(electron, heavy_hole, only_a, grid, target,
                  rung="plus_A_well_density_Nz",
                  changed="N_z: period density -> well density"),
        _evaluate(electron, heavy_hole, production, grid, target,
                  rung="plus_A_and_B_zincblende_zone",
                  changed="and BZ edge: pi/a -> 2*pi/a"),
    ]
    values = [rung.chi2_at_target_pm_per_V for rung in rungs]
    factor_a = values[1] / values[0] if values[0] else None
    factor_b = values[2] / values[1] if values[1] else None
    record = {
        "target_wavelength_nm": target,
        "units": "pm/V",
        "evaluated_on": "this run's solved envelopes; no re-solve",
        "rungs": [rung.as_record() for rung in rungs],
        "factor_A_well_density_Nz": factor_a,
        "factor_B_zincblende_zone_edge": factor_b,
        "factor_A_times_B": (
            None if factor_a is None or factor_b is None else factor_a * factor_b
        ),
        "correction_C_measured_here": False,
        "correction_C_note": (
            "Correction C changed the deck, so it has no post-processing switch "
            "and cannot be ablated on one run. It is measured in "
            "'versus_baseline' as this run's legacy-settings value against the "
            "value Demo 16E recorded for the same structure."
        ),
    }
    # N_z enters Eq. 2 linearly, so this one has a known answer and a wrong
    # answer here means the settings did not reach the evaluator.
    if factor_a is not None and not math.isclose(factor_a, 2.0, rel_tol=1e-9):
        raise Demo17Error(
            f"correction A measured {factor_a:.9f}x, but N_z enters Eq. 2 "
            "linearly and the change is exactly 2x. The settings did not reach "
            "the evaluator."
        )
    return record


def versus_baseline(
    ablation: Mapping[str, Any],
    corrected_pm_per_V: float,
    baseline_pm_per_V: float | None,
    *,
    baseline_source: str,
) -> dict[str, Any]:
    """Split the total change against Demo 16E into (C) and (A x B).

    ``baseline_pm_per_V`` is Demo 16E's recorded value for the SAME case. When
    it is unavailable the factorisation is reported as unavailable rather than
    guessed -- an absent baseline is not a baseline of 1.
    """

    rungs = {row["rung"]: row for row in ablation["rungs"]}
    legacy_on_new_states = rungs["legacy"]["chi2_at_target_pm_per_V"]
    if baseline_pm_per_V is None or not baseline_pm_per_V:
        return {
            "baseline_available": False,
            "baseline_source": baseline_source,
            "note": (
                "no Demo 16E value for this case; correction C's factor and the "
                "total ratio are not computable and are not estimated."
            ),
            "chi2_legacy_settings_on_demo17_states_pm_per_V": legacy_on_new_states,
            "chi2_corrected_pm_per_V": corrected_pm_per_V,
        }
    factor_c = legacy_on_new_states / float(baseline_pm_per_V)
    total = corrected_pm_per_V / float(baseline_pm_per_V)
    return {
        "baseline_available": True,
        "baseline_source": baseline_source,
        "chi2_demo16e_recorded_pm_per_V": float(baseline_pm_per_V),
        "chi2_legacy_settings_on_demo17_states_pm_per_V": legacy_on_new_states,
        "chi2_corrected_pm_per_V": corrected_pm_per_V,
        "factor_C_wider_dirichlet_box": factor_c,
        "factor_A_times_B": ablation.get("factor_A_times_B"),
        "factor_total": total,
        "factor_consistency_residual": (
            None if ablation.get("factor_A_times_B") is None
            else abs(total - factor_c * float(ablation["factor_A_times_B"]))
            / max(abs(total), 1e-30)
        ),
    }


def load_baseline_chi2(path: Path | None = None) -> dict[str, float]:
    """Demo 16E's recorded chi2(1550) per case, when a summary is available."""

    summary = Path(path) if path else DEFAULT_BASELINE_SUMMARY
    if not summary.is_file():
        return {}
    try:
        payload = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    values: dict[str, float] = {}
    for record in payload.get("cases", []):
        optical = record.get("optical") or {}
        value = optical.get("chi2_at_1550")
        if record.get("case_id") and value is not None:
            values[str(record["case_id"])] = float(value)
    return values


# ---------------------------------------------------------------------------
# Bound-state verdict and the paper comparison
# ---------------------------------------------------------------------------


def bound_state_verdict(extracted: Path) -> dict[str, Any]:
    """The strict per-state verdict, applied to the states Eq. 2 actually used.

    The config runs Demo 11 under ``quasi_bound_state_policy: warn`` so that a
    failing state still leaves its envelope on disk to be diagnosed. The strict
    verdict is applied here instead, per state, and only over the states inside
    Eq. 2's window -- a state the sum never sees cannot invalidate it.

    ``certified`` is deliberately tri-state. ``None`` means the question was not
    answered (no file, unrecognised schema, a required state missing), and no
    caller may read that as success. Correction C is supposed to turn this from
    Demo 16E's False into True; being unable to tell is a different outcome from
    passing.
    """

    path = Path(extracted) / "quasi_bound_states.json"
    if not path.is_file():
        return {"certified": None, "reason": f"{path.name} was not written",
                "states": [], "failing": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"certified": None, "reason": f"{type(exc).__name__}: {exc}",
                "states": [], "failing": []}
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return {"certified": None, "reason": "no per-state records",
                "states": [], "failing": []}
    required = {("electron", 1), ("electron", 2), ("heavy_hole", 1), ("heavy_hole", 2)}
    in_window, seen = [], set()
    for row in records:
        if not isinstance(row, Mapping):
            return {"certified": None, "reason": "unrecognised record schema",
                    "states": [], "failing": []}
        if "within_chi2_state_window" not in row:
            return {"certified": None,
                    "reason": "records predate within_chi2_state_window; schema "
                              "not recognised, verdict NOT certified",
                    "states": [], "failing": []}
        if not row["within_chi2_state_window"]:
            continue
        seen.add((str(row.get("band")), int(row.get("state", 0))))
        in_window.append(row)
    missing = sorted(required - seen)
    if missing:
        return {
            "certified": None,
            "reason": f"states not present in Eq. 2's window: {missing}",
            "states": [_state_verdict(row) for row in in_window],
            "failing": [],
        }
    states = [_state_verdict(row) for row in in_window]
    failing = [row for row in states if row["verdict"] != "PASS"]
    return {
        "certified": not failing,
        "reason": (
            "all four states in Eq. 2's window pass the bound criterion and the "
            "boundary-probability threshold"
            if not failing else
            "; ".join(f"{row['band']} {row['state']}: {row['detail']}"
                      for row in failing)
        ),
        "maximum_boundary_probability_threshold": payload.get(
            "maximum_boundary_probability"
        ),
        "policy_used_for_analysis": payload.get("policy"),
        "states": states,
        "failing": failing,
    }


def _state_verdict(row: Mapping[str, Any]) -> dict[str, Any]:
    passes = row.get("passes_bound_criterion")
    boundary_ok = bool(row.get("boundary_probability_within_threshold"))
    if passes is None:
        verdict = "NOT_TESTED"
    elif passes and boundary_ok:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    return {
        "band": row.get("band"),
        "state": row.get("state"),
        "energy_eV": row.get("energy_eV"),
        "boundary_probability": row.get("boundary_probability"),
        "verdict": verdict,
        "detail": row.get("exclusion_reason") or row.get("bound_criterion_detail") or "",
    }


def paper_comparison(
    cfg: Mapping[str, Any], case: cases17.GeometryCase, optical: Mapping[str, Any]
) -> dict[str, Any] | None:
    """The abrupt case against the paper's stated 2340 pm/V.

    Returns ``None`` for the other nine, because the paper does not state an
    absolute value for them and inventing a comparison would be worse than
    having none.
    """

    if not case.is_paper_target:
        return None
    reference = cfg["paper_reference"]
    target = float(reference["expectations"]["chi2_ideal_abrupt_pm_per_V"])
    value = optical.get("chi2_at_1550")
    resonance_target = float(reference["expectations"]["simulated_resonance_nm"])
    low, high = (float(v) for v in reference["plausibility_band_pm_per_V"])
    if value is None:
        return {"case_id": case.case_id, "target_pm_per_V": target,
                "computed_pm_per_V": None, "comparable": False,
                "reason": "the optical analysis produced no value"}
    value = float(value)
    peak = optical.get("spectral_peak_wavelength_nm")
    return {
        "case_id": case.case_id,
        "structure": "ideal abrupt 7.1 / 1.8 / 2.9 nm, s = 0.42",
        "target_pm_per_V": target,
        "target_source": "arXiv:2602.23246v1 Section 3.1, stated in words",
        "computed_pm_per_V": value,
        "comparable": True,
        "ratio_target_over_computed": target / value if value else None,
        "remaining_factor": target / value if value else None,
        "within_plausibility_band": bool(low <= value <= high),
        "plausibility_band_pm_per_V": [low, high],
        "resonance_target_nm": resonance_target,
        "resonance_computed_nm": peak,
        "resonance_error_nm": (
            None if peak is None else float(peak) - resonance_target
        ),
        "interpretation": (
            "The resonance position and the structural trends were already "
            "reproduced by Demo 16E; what is under test here is only the "
            "absolute magnitude. A remaining factor is reported, never applied."
        ),
    }


# ---------------------------------------------------------------------------
# Optical analysis
# ---------------------------------------------------------------------------


def analyse_optics(
    cfg: Mapping[str, Any], case: cases17.GeometryCase, case_dir: Path,
    raw_output: Path, *, baseline_chi2: Mapping[str, float] | None = None,
    baseline_source: str = "demo_results/demo_16E/physics_summary.json",
) -> dict[str, Any]:
    """Demo 11/14's absolute chi(2), plus Demo 17's ablation and verdicts.

    The spectrum itself is the production one, evaluated exactly as Demo 16E
    evaluates it -- only the settings differ. The 1550 nm value is interpolated
    from that spectrum and cross-checked against the production evaluation of
    the same quantity, because the curve and the number in the table disagreeing
    would mean they came from different calculations.
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
    spectrum_path = parsed / "chi2_focused.csv"
    if not spectrum_path.is_file():
        raise Demo17Error(f"production optical analysis did not write {spectrum_path}")
    spectrum = np.loadtxt(spectrum_path, delimiter=",", skiprows=1)
    wavelength = np.asarray(spectrum[:, 0], dtype=float)
    magnitude = np.asarray(spectrum[:, 3], dtype=float)
    chi2_1550 = float(np.interp(TARGET_WAVELENGTH_NM, wavelength, magnitude))
    peak_index = int(np.argmax(magnitude))
    peak_nm = float(wavelength[peak_index])
    peak_magnitude = float(magnitude[peak_index])
    production_value = metrics.get("chi2_relative_at_reference")
    if production_value is not None and not np.isclose(
        chi2_1550, float(production_value), rtol=1e-10, atol=1e-12
    ):
        raise Demo17Error(
            "1550 nm spectrum interpolation disagrees with production evaluation: "
            f"{chi2_1550} versus {production_value}"
        )
    if str(metrics.get("chi2_mode")) != "absolute" or "pm/V" not in str(
        metrics.get("chi2_units", "")
    ):
        raise Demo17Error(
            "Demo 17 reports pm/V and the analysis did not return absolute "
            f"units: mode={metrics.get('chi2_mode')!r}, "
            f"units={metrics.get('chi2_units')!r}."
        )

    ablation = correction_ablation(cfg, parsed, metrics)
    # The ablation's top rung and the production spectrum are two paths to one
    # number; if they disagree the ablation is describing a different
    # calculation from the one in the table.
    top = ablation["rungs"][-1]["chi2_at_target_pm_per_V"]
    if not math.isclose(top, chi2_1550, rel_tol=1e-6, abs_tol=1e-9):
        raise Demo17Error(
            f"the ablation's corrected rung gives {top} pm/V but the production "
            f"spectrum gives {chi2_1550} pm/V at {TARGET_WAVELENGTH_NM} nm."
        )
    baseline = dict(baseline_chi2 or {})
    comparison = versus_baseline(
        ablation, chi2_1550, baseline.get(case.case_id),
        baseline_source=baseline_source,
    )

    result = {
        "passed": True,
        "case_id": case.case_id,
        "demo17_version": DEMO_VERSION,
        "target_wavelength_nm": TARGET_WAVELENGTH_NM,
        "chi2_at_1550": chi2_1550,
        "chi2_units": metrics.get("chi2_units"),
        "spectral_peak_wavelength_nm": peak_nm,
        "spectral_peak_chi2": peak_magnitude,
        "detuning_from_1550_nm": peak_nm - TARGET_WAVELENGTH_NM,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "scan_window_nm": [float(wavelength[0]), float(wavelength[-1])],
        "spectrum_path": str(spectrum_path),
        "analysis_settings_path": str(parsed / "chi2_settings.json"),
        "selected_states_path": str(parsed / "state_count_audit.json"),
        "correction_ablation": ablation,
        "versus_demo16e_baseline": comparison,
        "bound_state_verdict": bound_state_verdict(parsed),
        "deck_geometry": deck_geometry_record(cfg, case),
        "paper_comparison": paper_comparison(cfg, case, {
            "chi2_at_1550": chi2_1550,
            "spectral_peak_wavelength_nm": peak_nm,
        }),
        "production_metrics": metrics,
    }
    runlog14.write_json_atomic(optical_root / "optical_result.json", result)
    return result


# ---------------------------------------------------------------------------
# Cross-case comparisons -- Demo 16E's, plus Demo 17's correction columns
# ---------------------------------------------------------------------------


energy_shifts = demo16e.energy_shifts
derived_energies = demo16e.derived_energies
composition_difference = demo16e.composition_difference
equivalence_report = demo16e.equivalence_report
abrupt_vs_graded_report = demo16e.abrupt_vs_graded_report
add_reference_shifts = demo16e.add_reference_shifts
overlap_geometry = demo16e.overlap_geometry
render_method = demo16e.render_method
representation_of = demo16e.representation_of


def master_row(
    case: cases17.GeometryCase, record: Mapping[str, Any],
    comparison: Mapping[str, Any], representation: str,
) -> dict[str, Any]:
    """Demo 16E's master row, plus the correction columns Demo 17 adds."""

    row = dict(demo16e.master_row(case, record, comparison, representation))
    optical = record.get("optical") or {}
    ablation = optical.get("correction_ablation") or {}
    baseline = optical.get("versus_demo16e_baseline") or {}
    verdict = optical.get("bound_state_verdict") or {}
    geometry = optical.get("deck_geometry") or {}
    paper = optical.get("paper_comparison") or {}
    rungs = {r["rung"]: r for r in ablation.get("rungs", [])}
    row.update({
        "is_paper_target_case": case.is_paper_target,
        "chi2_legacy_settings_pm_per_V": (
            rungs.get("legacy", {}).get("chi2_at_target_pm_per_V")
        ),
        "factor_A_well_density_Nz": ablation.get("factor_A_well_density_Nz"),
        "factor_B_zincblende_zone_edge": ablation.get("factor_B_zincblende_zone_edge"),
        "factor_A_times_B": ablation.get("factor_A_times_B"),
        "chi2_demo16e_recorded_pm_per_V": baseline.get(
            "chi2_demo16e_recorded_pm_per_V"
        ),
        "factor_C_wider_dirichlet_box": baseline.get("factor_C_wider_dirichlet_box"),
        "factor_total_vs_demo16e": baseline.get("factor_total"),
        "bound_states_certified": verdict.get("certified"),
        "bound_states_failing": len(verdict.get("failing") or []),
        "max_boundary_probability": max(
            [row.get("boundary_probability") or 0.0
             for row in verdict.get("states") or []] or [None]
        ) if verdict.get("states") else None,
        "quantum_region_width_nm": geometry.get("quantum_region_width_nm"),
        "dirichlet_clearance_nm": geometry.get("dirichlet_clearance_left_nm"),
        "paper_target_pm_per_V": paper.get("target_pm_per_V"),
        "paper_remaining_factor": paper.get("remaining_factor"),
    })
    return row


def study_summary(
    cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The one-paragraph answer: what the three corrections were worth."""

    def _finite(key: str) -> list[float]:
        return [
            float(row[key]) for row in rows
            if row.get(key) is not None and np.isfinite(float(row[key]))
        ]

    target_row = next(
        (row for row in rows if row.get("is_paper_target_case")), None
    )
    factors_ab = _finite("factor_A_times_B")
    factors_c = _finite("factor_C_wider_dirichlet_box")
    factors_total = _finite("factor_total_vs_demo16e")
    certified = [row.get("bound_states_certified") for row in rows]
    return {
        "demo_id": DEMO_ID,
        "demo17_version": DEMO_VERSION,
        "cases_reported": len(rows),
        "corrections": corrections_record(cfg),
        "factor_A_times_B": {
            "cases": len(factors_ab),
            "min": min(factors_ab) if factors_ab else None,
            "median": float(np.median(factors_ab)) if factors_ab else None,
            "max": max(factors_ab) if factors_ab else None,
        },
        "factor_C_wider_dirichlet_box": {
            "cases": len(factors_c),
            "min": min(factors_c) if factors_c else None,
            "median": float(np.median(factors_c)) if factors_c else None,
            "max": max(factors_c) if factors_c else None,
        },
        "factor_total_vs_demo16e": {
            "cases": len(factors_total),
            "min": min(factors_total) if factors_total else None,
            "median": float(np.median(factors_total)) if factors_total else None,
            "max": max(factors_total) if factors_total else None,
        },
        "bound_states_certified": {
            "true": sum(1 for value in certified if value is True),
            "false": sum(1 for value in certified if value is False),
            "not_certified": sum(1 for value in certified if value is None),
        },
        "paper_target": {
            "case_id": cases17.PAPER_TARGET_CASE_ID,
            "target_pm_per_V": cases17.PAPER_TARGET_PM_PER_V,
            "computed_pm_per_V": (
                None if target_row is None else target_row.get("chi2_at_1550")
            ),
            "remaining_factor": (
                None if target_row is None
                else target_row.get("paper_remaining_factor")
            ),
        },
        "known_open_factors_not_applied": (
            cfg.get("corrections") or {}
        ).get("known_open_factors"),
        "no_scale_factor_was_fitted": True,
    }


def write_corrections_manifest(path: Path, cfg: Mapping[str, Any]) -> Path:
    """Stamp the three corrections beside every run, before anything is solved."""

    return runlog14.write_text_atomic(
        Path(path),
        yaml.safe_dump(corrections_record(cfg), sort_keys=False,
                       default_flow_style=False),
    )
