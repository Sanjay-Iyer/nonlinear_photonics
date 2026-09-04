"""Compare Demo 21 and the exploratory non-parabolic chi(2) model.

This is a solver-free, apples-to-apples comparison.  It reads the licensed
Demo 21 Case 04 zone-centre energies and envelope matrix elements, holds them
fixed, and changes only the in-plane dispersion used in the optical
denominators:

* Demo 21: one parabolic reduced-mass transition shift.
* Hybrid: the four polynomial band dispersions from
  ``docs/8_band_non_parabolic_v2.py``.

The script also shows the two disputed scale conventions so that a change of
spectral shape cannot be mistaken for a change of normalization.  It does not
run nextnano++ and it is not a substitute for a k-resolved 8-band solve.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
TRACE_DIR = HERE / "trace_linear_1nm"
ENERGIES_CSV = TRACE_DIR / "05_subband_energies.csv"
MATRIX_ELEMENTS_CSV = TRACE_DIR / "07_matrix_elements.csv"
DEFAULT_OUTPUT = HERE / "hybrid_vs_demo21_paper_full_spectrum.png"

HC_EV_NM = 1239.841984
HBAR_J_S = 1.054571817e-34
E_CHARGE_C = 1.602176634e-19
M0_KG = 9.1093837015e-31
GAMMA_EV = 0.005

# Demo 21's absolute Eq. 2 prefactor after its nm/eV -> SI conversion.
DEMO21_PREFACTOR_PM_PER_V = 56.69816882497043
DEMO21_BARE_D2K_FACTOR = (2.0 * math.pi) ** 2

# Relative to the repository's spin-degenerate radial Eq. 2 convention, the
# exploratory script omits 1/6 and uses 2 integral(k dk) instead of
# (1/pi) integral(k dk), giving a net factor 12*pi.
HYBRID_AS_WRITTEN_FACTOR = 12.0 * math.pi

PAPER_DIGITIZED = np.array(
    [
        [400, 100], [450, 180], [500, 450], [540, 1260], [560, 680],
        [580, 200], [605, 0], [630, 220], [660, 500], [700, 950],
        [730, 1500], [760, 2450], [785, 1550], [815, 1200], [850, 1100],
        [900, 1120], [950, 1220], [1000, 1450], [1040, 1950], [1080, 3250],
        [1105, 2050], [1130, 1850], [1150, 1150], [1175, 1180], [1200, 1050],
        [1225, 750], [1250, 750], [1275, 350], [1300, 350], [1330, 0],
        [1360, 200], [1400, 600], [1440, 1050], [1480, 1800], [1500, 2600],
        [1520, 3950], [1540, 2900], [1560, 1950], [1580, 1450], [1600, 1250],
        [1650, 1050], [1700, 950], [1750, 850], [1800, 750], [1850, 700],
    ],
    dtype=float,
)


def read_demo21_inputs() -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    """Read E_e, E_hh, overlap O, and position matrices from Demo 21."""
    with ENERGIES_CSV.open(newline="", encoding="utf-8") as handle:
        energies = {row["state"]: float(row["energy_eV"]) for row in csv.DictReader(handle)}

    electron = np.array([energies["e1"], energies["e2"]], dtype=float)
    hole = np.array([energies["hh1"], energies["hh2"]], dtype=float)
    overlap = np.zeros((2, 2), dtype=float)
    z_e = np.zeros((2, 2), dtype=float)
    z_hh = np.zeros((2, 2), dtype=float)
    e_index = {"e1": 0, "e2": 1}
    h_index = {"hh1": 0, "hh2": 1}

    with MATRIX_ELEMENTS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            value = float(row["value"])
            if row["symbol"] == "O":
                overlap[e_index[row["row"]], h_index[row["col"]]] = value
            elif row["symbol"] == "z_e":
                z_e[e_index[row["row"]], e_index[row["col"]]] = value
            elif row["symbol"] == "z_hh":
                z_hh[h_index[row["row"]], h_index[row["col"]]] = value

    return electron, hole, overlap, z_e, z_hh


def trapezoid_k_weights(k_per_nm: np.ndarray) -> np.ndarray:
    """Weights for spin-2 integral d^2k/(2*pi)^2 = integral k dk/pi."""
    step = float(k_per_nm[1] - k_per_nm[0])
    weights = k_per_nm * step / math.pi
    weights[[0, -1]] *= 0.5
    return weights


def transition_energies(
    electron: np.ndarray,
    hole: np.ndarray,
    *,
    model: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return k grid and transition cube DeltaE[n, m, k] in eV."""
    if model == "parabolic":
        k = np.linspace(0.0, 0.1 * math.pi / 0.565325, 96)
        reduced_mass_m0 = 1.0 / (1.0 / 0.067 + 1.0 / 0.112)
        kinetic_eV = (
            HBAR_J_S**2 * (k * 1.0e9) ** 2
            / (2.0 * reduced_mass_m0 * M0_KG)
            / E_CHARGE_C
        )
        transitions = (
            electron[:, None, None]
            - hole[None, :, None]
            + kinetic_eV[None, None, :]
        )
        return k, transitions

    if model != "hybrid":
        raise ValueError(f"unknown dispersion model: {model}")

    k = np.linspace(0.0, 1.2, 300)
    k_angstrom = 0.1 * k
    e1 = electron[0] + 54.492 * k_angstrom**2 - 851.1 * k_angstrom**4
    e2 = electron[1] + 50.864 * k_angstrom**2 - 732.61 * k_angstrom**4
    h1 = (
        hole[0]
        - 6.9771 * k_angstrom**2
        - 716.47 * k_angstrom**4
        + 36809.0 * k_angstrom**6
    )
    h2 = hole[1] - 10.165 * k_angstrom**2
    bands = np.vstack([e1, e2, h1, h2])
    transitions = np.empty((2, 2, k.size), dtype=float)
    for n in range(2):
        for m in range(2):
            transitions[n, m] = np.abs(bands[n] - bands[2 + m])
    return k, transitions


def chi2_spectrum(
    wavelengths_nm: np.ndarray,
    electron: np.ndarray,
    hole: np.ndarray,
    overlap: np.ndarray,
    z_e: np.ndarray,
    z_hh: np.ndarray,
    *,
    model: str,
) -> np.ndarray:
    """Evaluate the 16-term Eq. 2 state sum and return complex chi(2)."""
    k, transitions = transition_energies(electron, hole, model=model)
    weights = trapezoid_k_weights(k)
    result = np.zeros(wavelengths_nm.size, dtype=np.complex128)

    for iw, wavelength in enumerate(wavelengths_nm):
        photon_eV = HC_EV_NM / float(wavelength)
        total_at_k = np.zeros(k.size, dtype=np.complex128)
        for m in range(2):
            for n in range(2):
                two_photon = transitions[n, m] - 2.0 * photon_eV + 1j * GAMMA_EV
                for ell in range(2):
                    numerator = overlap[n, m] * z_e[n, ell] * overlap[ell, m]
                    one_photon = transitions[ell, m] - photon_eV + 1j * GAMMA_EV
                    total_at_k += numerator / (two_photon * one_photon)
                for ell in range(2):
                    numerator = overlap[n, m] * z_hh[m, ell] * overlap[n, ell]
                    one_photon = transitions[n, ell] - photon_eV + 1j * GAMMA_EV
                    total_at_k -= numerator / (two_photon * one_photon)

        result[iw] = DEMO21_PREFACTOR_PM_PER_V * np.dot(weights, total_at_k)
    return result


def peak(wavelengths_nm: np.ndarray, magnitude: np.ndarray) -> tuple[float, float]:
    index = int(np.argmax(magnitude))
    return float(wavelengths_nm[index]), float(magnitude[index])


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1]), text, font=font, fill=fill)


def _draw_rotated_label(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    box = font.getbbox(text)
    label = Image.new("RGBA", (box[2] - box[0] + 12, box[3] - box[1] + 12), (0, 0, 0, 0))
    ImageDraw.Draw(label).text((6, 6 - box[1]), text, font=font, fill=fill)
    rotated = label.rotate(90, expand=True)
    image.alpha_composite(rotated, (xy[0] - rotated.width // 2, xy[1] - rotated.height // 2))


def _draw_panel(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    *,
    title: str,
    ylabel: str,
    series: list[dict[str, object]],
    y_max: float,
    y_ticks: list[float],
    annotate: tuple[str, ...] = (),
) -> None:
    """Draw one publication-style Cartesian panel using Pillow only."""
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = bounds
    plot_left, plot_right = left + 140, right - 45
    plot_top, plot_bottom = top + 105, bottom - 85
    foreground = (25, 25, 25)
    muted = (92, 92, 92)
    grid = (220, 224, 229)
    border = (150, 156, 164)
    panel_font = _font(29, bold=True)
    legend_font = _font(19)
    tick_font = _font(19)
    axis_font = _font(23)

    draw.text((left, top), title, font=panel_font, fill=foreground)

    legend_x, legend_y = plot_left, top + 46
    for item in series:
        label = str(item["label"])
        color = item["color"]
        draw.line((legend_x, legend_y + 10, legend_x + 34, legend_y + 10), fill=color, width=5)
        draw.text((legend_x + 44, legend_y), label, font=legend_font, fill=foreground)
        label_width = draw.textbbox((0, 0), label, font=legend_font)[2]
        legend_x += 44 + label_width + 34

    x_min, x_max = 400.0, 1850.0
    sx = lambda value: plot_left + (float(value) - x_min) / (x_max - x_min) * (plot_right - plot_left)
    sy = lambda value: plot_bottom - float(value) / y_max * (plot_bottom - plot_top)

    for wavelength in range(400, 1801, 200):
        px = sx(wavelength)
        draw.line((px, plot_top, px, plot_bottom), fill=grid, width=2)
        text = str(wavelength)
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (box[2] - box[0]) / 2, plot_bottom + 11), text, font=tick_font, fill=muted)

    for value in y_ticks:
        py = sy(value)
        draw.line((plot_left, py, plot_right, py), fill=grid, width=2)
        text = f"{value:g}"
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((plot_left - 16 - (box[2] - box[0]), py - (box[3] - box[1]) / 2), text, font=tick_font, fill=muted)

    draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), outline=border, width=2)
    _draw_centered(draw, ((plot_left + plot_right) / 2, plot_bottom + 48), "Fundamental wavelength (nm)", axis_font, foreground)
    _draw_rotated_label(image, (left + 36, (plot_top + plot_bottom) // 2), ylabel, axis_font, foreground)

    for item in series:
        x = np.asarray(item["x"], dtype=float)
        y = np.asarray(item["y"], dtype=float)
        points = [(sx(xv), sy(np.clip(yv, 0.0, y_max))) for xv, yv in zip(x, y)]
        if item.get("dashed"):
            for index in range(0, len(points) - 1, 2):
                draw.line(points[index : min(index + 2, len(points))], fill=item["color"], width=5)
        else:
            draw.line(points, fill=item["color"], width=5, joint="curve")

        if item.get("points"):
            for xv, yv in zip(x, y):
                px, py = sx(xv), sy(np.clip(yv, 0.0, y_max))
                draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=item["color"])

        if str(item["id"]) in annotate:
            peak_nm, peak_value = peak(x, y)
            px, py = sx(peak_nm), sy(min(peak_value, y_max))
            draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=item["color"], outline=(255, 255, 255), width=2)
            label = f"{peak_nm:.0f} nm"
            draw.text((px + 11, max(plot_top + 5, py - 32)), label, font=tick_font, fill=item["color"])


def make_figure(output: Path) -> dict[str, float]:
    electron, hole, overlap, z_e, z_hh = read_demo21_inputs()
    wavelengths = np.arange(400.0, 1850.0 + 1.0, 2.0)
    paper = np.interp(wavelengths, PAPER_DIGITIZED[:, 0], PAPER_DIGITIZED[:, 1])
    demo_raw = np.abs(
        chi2_spectrum(
            wavelengths, electron, hole, overlap, z_e, z_hh, model="parabolic"
        )
    )
    hybrid_eq2 = np.abs(
        chi2_spectrum(
            wavelengths, electron, hole, overlap, z_e, z_hh, model="hybrid"
        )
    )
    demo_scaled = demo_raw * DEMO21_BARE_D2K_FACTOR
    hybrid_as_written = hybrid_eq2 * HYBRID_AS_WRITTEN_FACTOR

    at_1550 = int(np.flatnonzero(wavelengths == 1550.0)[0])
    expected_demo21 = 18.04752050786078
    if not np.isclose(demo_raw[at_1550], expected_demo21, rtol=1e-12, atol=1e-12):
        raise RuntimeError(
            "Demo 21 reconstruction failed: "
            f"{demo_raw[at_1550]} != {expected_demo21} pm/V"
        )

    colors = {
        "paper": (30, 30, 30),
        "demo": (217, 119, 6),
        "hybrid": (21, 128, 61),
        "demo_scaled": (219, 39, 119),
        "hybrid_written": (109, 40, 217),
    }
    image = Image.new("RGBA", (2400, 2700), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = _font(43, bold=True)
    subtitle_font = _font(23)
    _draw_centered(
        draw,
        (1200, 32),
        "Full-spectrum comparison: paper, Demo 21, and hybrid non-parabolic chi2",
        title_font,
        (20, 20, 20),
    )
    _draw_centered(
        draw,
        (1200, 88),
        "Same licensed Demo 21 Case 04 states; only the in-plane dispersion changes in the hybrid comparison",
        subtitle_font,
        (85, 85, 85),
    )

    _draw_panel(
        image,
        (55, 145, 2345, 950),
        title="A. Current code conventions - amplitudes are not directly comparable",
        ylabel="|chi2| (pm/V)",
        y_max=4500.0,
        y_ticks=[0, 1000, 2000, 3000, 4000],
        annotate=("paper", "hybrid_written"),
        series=[
            {"id": "paper", "label": "Paper Fig. 2d", "x": wavelengths, "y": paper, "color": colors["paper"], "dashed": True},
            {"id": "demo_scaled", "label": "Demo 21 x(2pi)^2", "x": wavelengths, "y": demo_scaled, "color": colors["demo_scaled"]},
            {"id": "hybrid_written", "label": "Hybrid as written", "x": wavelengths, "y": hybrid_as_written, "color": colors["hybrid_written"]},
        ],
    )
    _draw_panel(
        image,
        (55, 985, 2345, 1790),
        title="B. Same Eq. 2 normalization - dispersion-only comparison",
        ylabel="|chi2| (pm/V)",
        y_max=100.0,
        y_ticks=[0, 20, 40, 60, 80, 100],
        annotate=("demo", "hybrid"),
        series=[
            {"id": "demo", "label": "Demo 21 parabolic", "x": wavelengths, "y": demo_raw, "color": colors["demo"]},
            {"id": "hybrid", "label": "Hybrid non-parabolic", "x": wavelengths, "y": hybrid_eq2, "color": colors["hybrid"]},
        ],
    )
    _draw_panel(
        image,
        (55, 1825, 2345, 2630),
        title="C. Spectral shape - each curve normalized to its own maximum",
        ylabel="Normalized magnitude",
        y_max=1.08,
        y_ticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        series=[
            {"id": "paper", "label": "Paper", "x": wavelengths, "y": paper / np.max(paper), "color": colors["paper"], "dashed": True},
            {"id": "demo", "label": "Demo 21 parabolic", "x": wavelengths, "y": demo_raw / np.max(demo_raw), "color": colors["demo"]},
            {"id": "hybrid", "label": "Hybrid non-parabolic", "x": wavelengths, "y": hybrid_eq2 / np.max(hybrid_eq2), "color": colors["hybrid"]},
        ],
    )

    footer = (
        "Solver-free comparison. The hybrid curve changes E(k) only; "
        "it is not a new k-resolved 8-band nextnano++ solve."
    )
    _draw_centered(draw, (1200, 2662), footer, _font(20), (85, 85, 85))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", dpi=(200, 200), optimize=True)

    demo_peak_nm, demo_peak_value = peak(wavelengths, demo_raw)
    hybrid_peak_nm, hybrid_peak_value = peak(wavelengths, hybrid_eq2)
    return {
        "demo21_1550_pm_per_V": float(demo_raw[at_1550]),
        "hybrid_eq2_1550_pm_per_V": float(hybrid_eq2[at_1550]),
        "hybrid_as_written_1550_pm_per_V": float(hybrid_as_written[at_1550]),
        "demo21_peak_nm": demo_peak_nm,
        "demo21_peak_pm_per_V": demo_peak_value,
        "hybrid_peak_nm": hybrid_peak_nm,
        "hybrid_peak_pm_per_V": hybrid_peak_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metrics = make_figure(args.output.resolve())
    print(f"Saved: {args.output.resolve()}")
    for name, value in metrics.items():
        print(f"{name}: {value:.12g}")


if __name__ == "__main__":
    main()
