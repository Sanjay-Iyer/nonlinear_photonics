"""Generic nextnano++ deck builder for Demo 27.

One builder serves every sub-demo, because the campaign's central rule is that
each sub-demo makes exactly ONE controlled change against a single frozen
baseline. A per-sub-demo renderer would make that rule unenforceable; here the
baseline is the Demo 23 structure and every knob a sub-demo turns is a named
field on :class:`DeckSpec`, so the change is visible in the manifest and can be
diffed against the baseline deck.

Every construct emitted here already exists in a deck this repository has
validated:

* structure / grid / classical / kp_8band / dispersion / k_integration
  -- Demo 22 ``kp8_acqw22.in.j2`` and Demo 25 ``deck25.py``
* ``kp_6band{ num_ev }`` and single-band ``Gamma{}`` / ``HH{}``
  -- Demos 07, 08, 11-19 and ``inputs/01_smoke_tests/04_temperature_and_multiband``
* ``impurities{}`` / ``doping{ constant{} }`` / ``poisson{}`` /
  ``run{ quantum_poisson{} }``
  -- Demo 06 and ``inputs/01_smoke_tests/06_device_and_optical``

Nothing here is invented syntax, and ``--parse`` is still run over every deck in
preflight rather than trusted.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from . import Demo27Error

BAND_MODELS = ("kp8", "kp6", "single_band")
K_MODES = ("none", "dispersion", "integration", "integration_plus_dispersion")
ELECTROSTATICS = ("flat_band", "poisson", "quantum_poisson")
BOUNDARIES = ("dirichlet", "neumann")
INTERFACE_MODELS = ("abrupt", "linear_graded")


@dataclass(frozen=True)
class Doping:
    """A physically justified doping region. ``justification`` is mandatory."""

    name: str
    kind: str            # donor | acceptor
    start_nm: float
    end_nm: float
    conc_cm3: float
    degeneracy: int
    justification: str

    def __post_init__(self) -> None:
        if self.kind not in ("donor", "acceptor"):
            raise Demo27Error(f"doping kind must be donor or acceptor, got {self.kind!r}")
        if self.end_nm <= self.start_nm:
            raise Demo27Error(f"doping region {self.name!r} needs end_nm > start_nm")
        if not str(self.justification).strip():
            raise Demo27Error(
                f"doping region {self.name!r} has no justification. Demo 27 does not "
                "invent doping to manufacture a difference; state the physical source "
                "of the carriers in the sub-demo config or remove the region.")


@dataclass(frozen=True)
class DeckSpec:
    """Everything one Demo 27 deck may vary. Defaults are the Demo 23 baseline."""

    name: str
    question: str = ""

    # --- geometry -------------------------------------------------------------
    thick_well_nm: float = 7.1
    tunnel_barrier_nm: float = 1.8
    thin_well_nm: float = 2.9
    period_barrier_nm: float = 18.2
    interface_model: str = "linear_graded"
    grade_width_nm: float = 1.0
    quantum_region_padding_nm: float = 2.0

    # --- materials ------------------------------------------------------------
    barrier_al_fraction: float = 0.55
    well_al_fraction: float = 0.0
    temperature_K: float = 300.0

    # --- numerics -------------------------------------------------------------
    active_spacing_nm: float = 0.05
    outer_spacing_nm: float = 0.5
    boundary: str = "dirichlet"

    # --- quantum model --------------------------------------------------------
    band_model: str = "kp8"
    num_electrons: int = 6
    num_holes: int = 8
    output_state_count: int = 14

    # --- k space --------------------------------------------------------------
    k_mode: str = "dispersion"
    k_points: int = 301
    kmax_per_nm: float = 0.0
    relative_size: float = 0.10
    symmetry: str = "none"
    force_k0_subspace: bool = False
    k_point_subdirectories: bool = False
    direction_name: str = "y"
    direction: tuple = (0.0, 1.0, 0.0)

    # --- electrostatics -------------------------------------------------------
    electrostatics: str = "flat_band"
    doping: tuple = ()
    poisson_iterations: int = 100
    poisson_residual: float = 1.0e-6
    poisson_alpha: float = 0.3

    # --- harvest --------------------------------------------------------------
    harvest: Mapping = field(default_factory=dict)

    def __post_init__(self) -> None:
        checks = ((self.band_model, BAND_MODELS, "band_model"),
                  (self.k_mode, K_MODES, "k_mode"),
                  (self.electrostatics, ELECTROSTATICS, "electrostatics"),
                  (self.boundary, BOUNDARIES, "boundary"),
                  (self.interface_model, INTERFACE_MODELS, "interface_model"))
        for value, allowed, label in checks:
            if value not in allowed:
                raise Demo27Error(f"{label}={value!r} is not one of {allowed}")
        if self.output_state_count > self.num_electrons + self.num_holes:
            raise Demo27Error(
                f"deck {self.name}: output_state_count ({self.output_state_count}) exceeds the "
                f"{self.num_electrons + self.num_holes} states the solver will produce")
        if self.k_mode != "none" and self.k_points < 1:
            raise Demo27Error(f"deck {self.name}: k_points must be >= 1")
        if self.interface_model == "linear_graded" and self.grade_width_nm <= 0:
            raise Demo27Error(f"deck {self.name}: linear_graded needs a positive grade width")
        norm = math.sqrt(sum(v * v for v in self.direction))
        if not math.isclose(norm, 1.0, rel_tol=1e-9):
            raise Demo27Error(f"deck {self.name}: direction {self.direction} is not normalized")

    # --- derived geometry -----------------------------------------------------
    @property
    def outer_half_nm(self) -> float:
        return float(self.period_barrier_nm) / 2.0

    @property
    def interfaces(self) -> tuple:
        i1 = self.outer_half_nm
        i2 = i1 + float(self.thick_well_nm)
        i3 = i2 + float(self.tunnel_barrier_nm)
        i4 = i3 + float(self.thin_well_nm)
        return i1, i2, i3, i4

    @property
    def domain_end_nm(self) -> float:
        return self.interfaces[3] + self.outer_half_nm

    @property
    def quantum_window_nm(self) -> tuple:
        i1, _, _, i4 = self.interfaces
        pad = float(self.quantum_region_padding_nm)
        return i1 - pad, i4 + pad

    def with_changes(self, **changes: Any) -> "DeckSpec":
        return replace(self, **changes)


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------

def _structure_regions(spec: DeckSpec) -> str:
    i1, i2, i3, i4 = spec.interfaces
    al = float(spec.barrier_al_fraction)
    well = float(spec.well_al_fraction)
    end = spec.domain_end_nm
    alloy = 'ternary_constant{ name = "Al(x)Ga(1-x)As" alloy_x = %.9g }' % al
    lines = [
        "    region{ everywhere{} %s }" % alloy,
        "    region{ line{ x = [0, %.9g] } contact{ name = qw_contact } }" % end,
    ]
    if math.isclose(well, 0.0, abs_tol=1e-12):
        for lo, hi in ((i1, i2), (i3, i4)):
            lines.append('    region{ line{ x = [%.9g, %.9g] } binary{ name = "GaAs" } }' % (lo, hi))
    else:
        for lo, hi in ((i1, i2), (i3, i4)):
            lines.append('    region{ line{ x = [%.9g, %.9g] } '
                         'ternary_constant{ name = "Al(x)Ga(1-x)As" alloy_x = %.9g } }'
                         % (lo, hi, well))
    if spec.interface_model == "linear_graded":
        width = float(spec.grade_width_nm)
        for center, left, right in ((i1, al, well), (i2, well, al), (i3, al, well), (i4, well, al)):
            lo, hi = center - width / 2.0, center + width / 2.0
            lines.append('    region{ line{ x = [%.9g, %.9g] } '
                         'ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [%.9g, %.9g] '
                         'x = [%.9g, %.9g] } }' % (lo, hi, left, right, lo, hi))
    for dope in spec.doping:
        lines.append('    region{ line{ x = [%.9g, %.9g] } '
                     'doping{ constant{ name = "%s"  conc = %.6g } } }'
                     % (dope.start_nm, dope.end_nm, dope.name, dope.conc_cm3))
    return "\n".join(lines)


def _grid_lines(spec: DeckSpec) -> str:
    i1, i2, i3, i4 = spec.interfaces
    active, outer = float(spec.active_spacing_nm), float(spec.outer_spacing_nm)
    positions = [(0.0, outer), (i1, active), (i2, active), (i3, active), (i4, active),
                 (spec.domain_end_nm, outer)]
    return "\n".join("        line{ pos = %.9g spacing = %.9g }" % (pos, step)
                     for pos, step in positions)


def _impurities_block(spec: DeckSpec) -> str:
    if not spec.doping:
        return "# No doping: the structure carries no fixed charge."
    lines = ["impurities{"]
    for dope in spec.doping:
        lines.append('    %s{ name = "%s"  degeneracy = %d  fully_ionized{} }'
                     % (dope.kind, dope.name, int(dope.degeneracy)))
    lines.append("}")
    return "\n".join(lines)


def _poisson_block(spec: DeckSpec) -> str:
    if spec.electrostatics == "flat_band":
        return "# Flat band: no poisson{} block, so no electrostatic feedback exists."
    return "poisson{\n    output_potential{}\n    output_electric_field{}\n}"


def _k_block(spec: DeckSpec) -> str:
    lines = []
    wants_integration = spec.k_mode in ("integration", "integration_plus_dispersion")
    wants_path = spec.k_mode in ("dispersion", "integration_plus_dispersion")
    if wants_integration:
        lines += ["            k_integration{",
                  "                num_points = %d" % int(spec.k_points),
                  "                relative_size = %.9g" % float(spec.relative_size),
                  "                symmetry = %s" % spec.symmetry,
                  "                force_k0_subspace = %s"
                  % ("yes" if spec.force_k0_subspace else "no"),
                  "            }"]
    else:
        lines.append("            k_integration_disabled{}")
    if wants_path:
        endpoint = ", ".join("%.12g" % (v * float(spec.kmax_per_nm)) for v in spec.direction)
        lines += ["            dispersion{",
                  "                path{",
                  '                    name = "Gamma_to_%s"' % spec.direction_name,
                  "                    point{ k = [0, 0, 0] }",
                  "                    point{ k = [%s] }" % endpoint,
                  "                    num_points = %d" % int(spec.k_points),
                  "                }",
                  "                output_k_vectors{}",
                  "                output_dispersions{ max_num = %d }" % int(spec.output_state_count),
                  "                output_masses{ max_num = %d }" % int(spec.output_state_count),
                  "            }"]
    return "\n".join(lines)


def _model_block(spec: DeckSpec) -> str:
    if spec.band_model == "kp8":
        return "\n".join(["        kp_8band{",
                          "            num_electrons = %d" % int(spec.num_electrons),
                          "            num_holes     = %d" % int(spec.num_holes),
                          _k_block(spec),
                          "            classify_by_energy{}",
                          "        }"])
    if spec.band_model == "kp6":
        return "\n".join(["        Gamma{ num_ev = %d }" % int(spec.num_electrons),
                          "        kp_6band{",
                          "            num_ev = %d" % int(spec.num_holes),
                          _k_block(spec),
                          "        }"])
    return "\n".join(["        Gamma{ num_ev = %d }" % int(spec.num_electrons),
                      "        HH{    num_ev = %d }" % int(spec.num_holes)])


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


#: Which bands the optical output blocks are asked for, per quantum model.
#: nextnano++ rejects these blocks without a tag ("requires the presence of some
#: of 'Gamma X Delta L HH LH SO KP6 KP8 ...'"), and the two block families accept
#: DIFFERENT tag sets, which is why there are two tables. Both were read out of
#: ``nextnano++/keywords/keywords_nnp.xml`` for 2026_07_03 and confirmed with
#: ``--parse``: the matrix-element blocks take only single-model tags, while
#: ``transition_energies`` also takes the cross-band pair tags.
MATRIX_MODEL_TAGS = {"kp8": ("KP8",), "kp6": ("Gamma", "KP6"),
                     "single_band": ("Gamma", "HH")}
TRANSITION_MODEL_TAG = {"kp8": "KP8", "kp6": "Gamma_KP6", "single_band": "Gamma_HH"}


def _harvest_block(spec: DeckSpec) -> str:
    harvest = dict(spec.harvest)

    def on(key: str, default: bool = True) -> bool:
        return bool(harvest.get(key, default))

    all_k = spec.k_mode != "none"
    is_kp8 = spec.band_model == "kp8"
    matrix_tags = MATRIX_MODEL_TAGS[spec.band_model]
    transition_tag = TRANSITION_MODEL_TAG[spec.band_model]
    lines = ["        output_states{",
             "            max_num = %d" % int(spec.output_state_count)]
    if all_k:
        lines.append("            all_k_points = yes")
    lines.append("            envelopes = %s" % _yn(on("envelopes")))
    if is_kp8:
        lines += ["            envelopes_CB_HH_LH_SO = %s" % _yn(on("envelopes_CB_HH_LH_SO")),
                  "            probabilities = %s" % _yn(on("probabilities")),
                  "            probabilities_partial_CB_HH_LH_SO = %s"
                  % _yn(on("probabilities_partial_CB_HH_LH_SO")),
                  "            spinor_composition = %s" % _yn(on("spinor_composition")),
                  "            spinor_composition_CB_HH_LH_SO = %s"
                  % _yn(on("spinor_composition_CB_HH_LH_SO"))]
    else:
        lines.append("            probabilities = %s" % _yn(on("probabilities")))
    lines += ["            in_one_file = no", "        }"]

    if on("transition_energies"):
        inner = "all_k_points = yes  " if all_k else ""
        lines.append("        transition_energies{ %s%s{} }" % (inner, transition_tag))
    if on("dipole_moment_matrix_elements"):
        lines += ["        dipole_moment_matrix_elements{",
                  '            polarization{ name = "growth_z" re = [1, 0, 0] }']
        if all_k:
            lines.append("            all_k_points = yes")
        lines += ["            %s{}" % t for t in matrix_tags]
        lines.append("        }")
    if on("momentum_matrix_elements"):
        lines += ["        momentum_matrix_elements{",
                  '            polarization{ name = "growth_z" re = [1, 0, 0] }',
                  '            polarization{ name = "inplane_y" re = [0, 1, 0] }']
        if all_k:
            lines.append("            all_k_points = yes")
        lines += ["            %s{}" % t for t in matrix_tags]
        lines += ["            output_matrix_elements = yes",
                  "            output_oscillator_strengths = %s" % _yn(on("oscillator_strengths")),
                  "        }"]
    if spec.electrostatics == "quantum_poisson":
        lines += ["        output_subband_densities{}", "        output_quantum_densities{}"]
    return "\n".join(lines)


def _quantum_block(spec: DeckSpec) -> str:
    start, end = spec.quantum_window_nm
    no_density = "        no_density = yes\n" if spec.electrostatics != "quantum_poisson" else ""
    subdirs = "        k_point_subdirectories = yes\n" if spec.k_point_subdirectories else ""
    return ("quantum{\n"
            "    region{\n"
            '        name = "acqw"\n'
            "        x = [%.9g, %.9g]\n" % (start, end)
            + no_density
            + "        boundary{ x = %s }\n" % spec.boundary
            + subdirs
            + _model_block(spec) + "\n"
            + _harvest_block(spec) + "\n"
            "    }\n"
            "}")


def _run_block(spec: DeckSpec) -> str:
    if spec.electrostatics == "flat_band":
        return "run{\n    quantum{}\n}"
    if spec.electrostatics == "poisson":
        return "run{\n    poisson{}\n    quantum{}\n}"
    return ("run{\n"
            "    quantum_poisson{\n"
            "        iterations      = %d\n" % int(spec.poisson_iterations)
            + "        residual        = %.6g\n" % float(spec.poisson_residual)
            + "        alpha_potential = %.6g\n" % float(spec.poisson_alpha)
            + "        output_log      = yes\n"
            "    }\n"
            "}")


def _classical_block(spec: DeckSpec) -> str:
    lines = ["classical{", "    Gamma{}", "    HH{}", "    LH{}", "    SO{}",
             "    output_bandedges{ averaged = no }", "    output_bandgap{}"]
    if spec.electrostatics != "flat_band":
        lines += ["    output_carrier_densities{}", "    output_ionized_dopant_densities{}"]
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def render(spec: DeckSpec, *, sub_demo: str = "27", controlled_change: str = "") -> str:
    """Render one complete nextnano++ deck."""
    header = ["# Demo %s: %s" % (sub_demo, spec.name)]
    if spec.question:
        header.append("# Question: %s" % spec.question)
    header += ["# Controlled change vs the Demo 23 baseline: %s"
               % (controlled_change or "none (baseline reproduction)"),
               "# Generated file. Do not hand-edit: edit the sub-demo config.yaml or",
               "# framework/decks.py, then re-run --preflight.",
               ""]
    body = [
        "global{",
        "    simulate1D{}",
        "    temperature = %.9g" % float(spec.temperature_K),
        '    substrate{ name = "GaAs" }',
        "    crystal_zb{ x_hkl = [1, 0, 0]  y_hkl = [0, 1, 0] }",
        "}",
        "",
        _impurities_block(spec),
        "",
        "contacts{ fermi{ name = qw_contact  bias = 0.0 } }",
        "",
        "grid{",
        "    xgrid{",
        _grid_lines(spec),
        "    }",
        "}",
        "",
        "structure{",
        "    output_region_index{ boxes = no }",
        "    output_material_index{ boxes = no }",
        "    output_alloy_composition{ boxes = no }",
        _structure_regions(spec),
        "}",
        "",
        _classical_block(spec),
        "",
        _poisson_block(spec),
        "",
        _quantum_block(spec),
        "",
        _run_block(spec),
        "",
    ]
    return "\n".join(header + body)


def write(spec: DeckSpec, directory: Path, *, sub_demo: str = "27",
          controlled_change: str = "") -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("%s.in" % spec.name)
    path.write_text(render(spec, sub_demo=sub_demo, controlled_change=controlled_change),
                    encoding="utf-8", newline="\n")
    return path


_NUMBER = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
                     r"(?![A-Za-z0-9_.])")
_QUOTED = re.compile(r'"[^"]*"')


def _canonical_numbers(line: str) -> str:
    """Rewrite every numeric literal in canonical float form.

    ``temperature = 300.0`` and ``temperature = 300`` are the same deck. Comparing
    them as text would report a difference that does not exist, so the structural
    diff compares values rather than formatting -- while still catching a real
    change, because 300.0 and 300.1 canonicalize differently.

    Quoted spans are left alone. A material name is not a number, and rewriting
    the 1 in ``"Al(x)Ga(1-x)As"`` would make the diff report a change to the
    material that never happened.
    """
    out = []
    cursor = 0
    for match in _QUOTED.finditer(line):
        out.append(_NUMBER.sub(lambda m: repr(float(m.group(0))), line[cursor:match.start()]))
        out.append(match.group(0))
        cursor = match.end()
    out.append(_NUMBER.sub(lambda m: repr(float(m.group(0))), line[cursor:]))
    return "".join(out)


def structural_lines(text: str) -> list:
    """The part of a deck that describes the physical structure, comments removed.

    Used to prove a sub-demo changed only what it declared. Stops at ``quantum{``
    because the quantum block is where the model and k-space knobs live, and those
    are compared separately.
    """
    body = text[text.index("global{"):text.index("quantum{")]
    return [_canonical_numbers(line.rstrip()) for line in body.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def diff_against_baseline(baseline_text: str, deck_text: str) -> list:
    """Return differing structural lines as ``-baseline`` / ``+deck`` entries.

    A real diff, not a positional comparison: removing four graded-interface
    regions shifts every later line, and reporting those shifted lines as
    differences would bury the one change that actually happened.
    """
    import difflib  # noqa: PLC0415

    a, b = structural_lines(baseline_text), structural_lines(deck_text)
    if a == b:
        return []
    out = []
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        out.extend("-%s" % line.strip() for line in a[i1:i2])
        out.extend("+%s" % line.strip() for line in b[j1:j2])
    return out
