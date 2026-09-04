"""Run Phase 1 of the home-laptop chi(2) spectral-shape debug study.

Implemented experiments:
  00_BASELINE
  01_COMPLEX_COMPONENTS

The trusted Demo 20/21 implementation is imported read-only.  Required state
data must exist in ``docs/demo21/trace_linear_1nm``; this script has no
analytical or synthetic fallback and never invokes nextnano++.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEMO21_DOCS = ROOT / "docs" / "demo21"
TRACE = DEMO21_DOCS / "trace_linear_1nm"
PRODUCTION_DIR = ROOT / "nextnano" / "demos" / "20_quantum_well_interface_grading_scaled"

for required in (
    TRACE / "05_subband_energies.csv",
    TRACE / "07_matrix_elements.csv",
    TRACE / "13_chi2_spectrum.csv",
):
    if not required.is_file():
        raise FileNotFoundError(
            f"Required cached licensed Demo 21 input is missing: {required}. "
            "Synthetic states are forbidden for this study."
        )

sys.path.insert(0, str(PRODUCTION_DIR))
sys.path.insert(0, str(DEMO21_DOCS))
import s06_chi2 as production  # noqa: E402
import compare_demo21_hybrid_spectra as comparison  # noqa: E402


OUT = ROOT / "debug_chi2_spectral_shape"
BASELINE_DIR = OUT / "00_baseline"
COMPLEX_DIR = OUT / "01_complex_components"
MASTER = OUT / "MASTER_DEBUG_SUMMARY.csv"

WAVELENGTHS = np.arange(400.0, 1850.0 + 1.0, 1.0)
NODE1 = (550.0, 650.0)
NODE2 = (1200.0, 1400.0)
PAPER_POINTS = comparison.PAPER_DIGITIZED.copy()

COLORS = {
    "paper": (25, 25, 25),
    "demo": (217, 119, 6),
    "hybrid": (21, 128, 61),
    "real": (37, 99, 235),
    "imag": (220, 38, 127),
    "abs": (24, 24, 27),
    "phase_demo": (124, 58, 237),
    "phase_hybrid": (8, 145, 178),
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size=size)


def centered(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=text_font)
    draw.text((x - (box[2] - box[0]) / 2, y), text, font=text_font, fill=fill)


def rotated_label(
    image: Image.Image,
    x: int,
    y: int,
    text: str,
    text_font: ImageFont.FreeTypeFont,
) -> None:
    box = text_font.getbbox(text)
    layer = Image.new("RGBA", (box[2] - box[0] + 14, box[3] - box[1] + 14), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((7, 7 - box[1]), text, font=text_font, fill=(25, 25, 25))
    layer = layer.rotate(90, expand=True)
    image.alpha_composite(layer, (x - layer.width // 2, y - layer.height // 2))


def nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if low == high:
        return [low]
    return np.linspace(low, high, count + 1).tolist()


def draw_panel(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    *,
    title: str,
    ylabel: str,
    series: list[dict[str, object]],
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    vlines: Iterable[float] = (),
) -> None:
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = bounds
    plot_left, plot_right = left + 145, right - 45
    plot_top, plot_bottom = top + 105, bottom - 82
    foreground = (25, 25, 25)
    muted = (88, 88, 88)
    grid = (221, 225, 230)
    border = (148, 154, 162)

    draw.text((left, top), title, font=font(29, bold=True), fill=foreground)
    legend_x, legend_y = plot_left, top + 48
    for item in series:
        label = str(item["label"])
        color = item["color"]
        draw.line((legend_x, legend_y + 10, legend_x + 34, legend_y + 10), fill=color, width=5)
        draw.text((legend_x + 43, legend_y), label, font=font(19), fill=foreground)
        width = draw.textbbox((0, 0), label, font=font(19))[2]
        legend_x += 43 + width + 31

    x0, x1 = xlim
    y0, y1 = ylim
    sx = lambda value: plot_left + (float(value) - x0) / (x1 - x0) * (plot_right - plot_left)
    sy = lambda value: plot_bottom - (float(value) - y0) / (y1 - y0) * (plot_bottom - plot_top)

    x_step = 200.0 if x1 - x0 > 500 else 25.0
    first_tick = math.ceil(x0 / x_step) * x_step
    for value in np.arange(first_tick, x1 + 0.1, x_step):
        px = sx(value)
        draw.line((px, plot_top, px, plot_bottom), fill=grid, width=2)
        label = f"{value:g}"
        box = draw.textbbox((0, 0), label, font=font(19))
        draw.text((px - (box[2] - box[0]) / 2, plot_bottom + 11), label, font=font(19), fill=muted)

    for value in nice_ticks(y0, y1):
        py = sy(value)
        draw.line((plot_left, py, plot_right, py), fill=grid, width=2)
        label = f"{value:.2g}"
        box = draw.textbbox((0, 0), label, font=font(19))
        draw.text((plot_left - 15 - (box[2] - box[0]), py - 11), label, font=font(19), fill=muted)

    if y0 < 0.0 < y1:
        draw.line((plot_left, sy(0), plot_right, sy(0)), fill=(100, 100, 100), width=3)
    for value in vlines:
        if x0 <= value <= x1:
            px = sx(value)
            draw.line((px, plot_top, px, plot_bottom), fill=(140, 140, 140), width=2)

    draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), outline=border, width=2)
    centered(draw, (plot_left + plot_right) / 2, plot_bottom + 47, "Fundamental wavelength (nm)", font(23), foreground)
    rotated_label(image, left + 37, (plot_top + plot_bottom) // 2, ylabel, font(23))

    for item in series:
        x = np.asarray(item["x"], dtype=float)
        y = np.asarray(item["y"], dtype=float)
        mask = (x >= x0) & (x <= x1) & np.isfinite(y)
        points = [(sx(xv), sy(np.clip(yv, y0, y1))) for xv, yv in zip(x[mask], y[mask])]
        if item.get("dashed"):
            for index in range(0, len(points) - 1, 2):
                draw.line(points[index : index + 2], fill=item["color"], width=5)
        else:
            draw.line(points, fill=item["color"], width=5, joint="curve")


def save_figure(
    path: Path,
    *,
    title: str,
    subtitle: str,
    panels: list[dict[str, object]],
    footer: str,
) -> None:
    width = 2400
    panel_height = 750
    height = 145 + panel_height * len(panels) + 75
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    centered(draw, width / 2, 25, title, font(42, bold=True), (20, 20, 20))
    centered(draw, width / 2, 80, subtitle, font(22), (80, 80, 80))
    for index, panel in enumerate(panels):
        top = 135 + index * panel_height
        draw_panel(image, (55, top, width - 55, top + panel_height - 10), **panel)
    centered(draw, width / 2, height - 46, footer, font(19), (80, 80, 80))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG", dpi=(200, 200), optimize=True)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def demo21_states() -> production.CaseStates:
    electron, hole, overlap, z_e, z_hh = comparison.read_demo21_inputs()
    return production.CaseStates(
        case_id="04",
        electron_energies_eV=electron,
        hole_energies_eV=hole,
        overlap_electron_hole=overlap,
        position_matrix_electron_nm=z_e,
        position_matrix_hole_nm=z_hh,
        provenance="docs/demo21/trace_linear_1nm cached licensed Case 04",
    )


def reproduce_spectra() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    states = demo21_states()
    settings = production.Chi2Settings()
    demo = production.chi2_spectrum(states, WAVELENGTHS, settings).chi2
    electron, hole, overlap, z_e, z_hh = comparison.read_demo21_inputs()
    hybrid = comparison.chi2_spectrum(
        WAVELENGTHS, electron, hole, overlap, z_e, z_hh, model="hybrid"
    )
    paper = np.interp(WAVELENGTHS, PAPER_POINTS[:, 0], PAPER_POINTS[:, 1])

    # Freeze the baseline against every stored Demo 21 focused-spectrum value.
    with (TRACE / "13_chi2_spectrum.csv").open(newline="", encoding="utf-8") as handle:
        stored = list(csv.DictReader(handle))
    stored_wavelength = np.array([float(row["wavelength_nm"]) for row in stored])
    stored_complex = np.array(
        [
            complex(float(row["chi2_raw_real_pm_per_V"]), float(row["chi2_raw_imag_pm_per_V"]))
            for row in stored
        ]
    )
    reproduced = demo[np.searchsorted(WAVELENGTHS, stored_wavelength)]
    maximum_error = float(np.max(np.abs(reproduced - stored_complex)))
    if maximum_error > 1.0e-11:
        raise RuntimeError(
            f"Baseline is not frozen: max complex error versus Demo 21 is {maximum_error:.3e} pm/V"
        )
    return paper, demo, hybrid


def normalized_magnitude(values: np.ndarray) -> np.ndarray:
    magnitude = np.abs(values)
    maximum = float(np.max(magnitude))
    return magnitude / maximum if maximum else magnitude


def window_minimum(values: np.ndarray, window: tuple[float, float]) -> tuple[float, float]:
    mask = (WAVELENGTHS >= window[0]) & (WAVELENGTHS <= window[1])
    local = np.asarray(values)[mask]
    index = int(np.argmin(local))
    return float(WAVELENGTHS[mask][index]), float(local[index])


def dominant_peak(values: np.ndarray) -> tuple[float, float]:
    index = int(np.argmax(values))
    return float(WAVELENGTHS[index]), float(values[index])


def normalized_rmse(candidate: np.ndarray, paper_norm: np.ndarray) -> float:
    candidate = np.asarray(candidate, dtype=float)
    maximum = float(np.max(np.abs(candidate)))
    scaled = np.abs(candidate) / maximum if maximum else np.abs(candidate)
    return float(np.sqrt(np.mean((scaled - paper_norm) ** 2)))


def zero_crossings(real_values: np.ndarray, window: tuple[float, float]) -> list[float]:
    crossings: list[float] = []
    for index in range(WAVELENGTHS.size - 1):
        x0, x1 = WAVELENGTHS[index : index + 2]
        if x1 < window[0] or x0 > window[1]:
            continue
        y0, y1 = float(real_values[index]), float(real_values[index + 1])
        if y0 == 0.0:
            crossings.append(float(x0))
        elif y0 * y1 < 0.0:
            crossings.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)))
    return crossings


def phase_jump_degrees(values: np.ndarray, window: tuple[float, float]) -> float:
    mask = (WAVELENGTHS >= window[0]) & (WAVELENGTHS <= window[1])
    phase = np.unwrap(np.angle(values[mask]))
    return float(np.max(np.abs(np.diff(np.degrees(phase)))))


def phase_span_degrees(values: np.ndarray, window: tuple[float, float]) -> float:
    mask = (WAVELENGTHS >= window[0]) & (WAVELENGTHS <= window[1])
    phase = np.degrees(np.unwrap(np.angle(values[mask])))
    return float(np.max(phase) - np.min(phase))


def complex_at(values: np.ndarray, wavelength_nm: float | None) -> complex | None:
    if wavelength_nm is None:
        return None
    real = np.interp(wavelength_nm, WAVELENGTHS, values.real)
    imag = np.interp(wavelength_nm, WAVELENGTHS, values.imag)
    return complex(real, imag)


def phase1_metrics(paper: np.ndarray, demo: np.ndarray, hybrid: np.ndarray) -> dict[str, object]:
    paper_norm = paper / float(np.max(paper))
    result: dict[str, object] = {
        "paper_node1": window_minimum(paper_norm, NODE1),
        "paper_node2": window_minimum(paper_norm, NODE2),
    }
    for name, values in (("demo21", demo), ("hybrid", hybrid)):
        magnitude_norm = normalized_magnitude(values)
        real_abs_norm = np.abs(values.real) / float(np.max(np.abs(values.real)))
        crossings1 = zero_crossings(values.real, NODE1)
        crossings2 = zero_crossings(values.real, NODE2)
        at_crossing1 = complex_at(values, crossings1[0] if crossings1 else None)
        at_crossing2 = complex_at(values, crossings2[0] if crossings2 else None)
        magnitude_max = float(np.max(np.abs(values)))
        result[name] = {
            "node1": window_minimum(magnitude_norm, NODE1),
            "node2": window_minimum(magnitude_norm, NODE2),
            "dominant_peak": dominant_peak(magnitude_norm),
            "shape_rmse_magnitude": normalized_rmse(np.abs(values), paper_norm),
            "shape_rmse_abs_real": normalized_rmse(values.real, paper_norm),
            "real_node1": window_minimum(real_abs_norm, NODE1),
            "real_node2": window_minimum(real_abs_norm, NODE2),
            "real_crossings_node1": crossings1,
            "real_crossings_node2": crossings2,
            "imag_at_first_real_crossing_node1_pm_per_V": (
                None if at_crossing1 is None else at_crossing1.imag
            ),
            "magnitude_norm_at_first_real_crossing_node1": (
                None if at_crossing1 is None else abs(at_crossing1) / magnitude_max
            ),
            "imag_at_first_real_crossing_node2_pm_per_V": (
                None if at_crossing2 is None else at_crossing2.imag
            ),
            "magnitude_norm_at_first_real_crossing_node2": (
                None if at_crossing2 is None else abs(at_crossing2) / magnitude_max
            ),
            "phase_jump_node1_deg": phase_jump_degrees(values, NODE1),
            "phase_jump_node2_deg": phase_jump_degrees(values, NODE2),
            "phase_span_node1_deg": phase_span_degrees(values, NODE1),
            "phase_span_node2_deg": phase_span_degrees(values, NODE2),
        }
    return result


def run_baseline(paper: np.ndarray, demo: np.ndarray, hybrid: np.ndarray, metrics: dict[str, object]) -> None:
    paper_norm = paper / float(np.max(paper))
    demo_norm = normalized_magnitude(demo)
    hybrid_norm = normalized_magnitude(hybrid)
    save_figure(
        BASELINE_DIR / "00_full_spectrum.png",
        title="00 BASELINE - normalized full-spectrum shape",
        subtitle="Cached licensed Demo 21 Case 04 states; 400-1850 nm; no solver run and no synthetic fallback",
        footer="Every curve is normalized to its own maximum. Paper points are linearly interpolated only for the error metric.",
        panels=[{
            "title": "Paper versus parabolic and hybrid finite-k dispersion",
            "ylabel": "Normalized |chi2|",
            "series": [
                {"label": "Paper Fig. 2d", "x": WAVELENGTHS, "y": paper_norm, "color": COLORS["paper"], "dashed": True},
                {"label": "Demo 21 parabolic", "x": WAVELENGTHS, "y": demo_norm, "color": COLORS["demo"]},
                {"label": "Hybrid non-parabolic", "x": WAVELENGTHS, "y": hybrid_norm, "color": COLORS["hybrid"]},
            ],
            "xlim": (400.0, 1850.0),
            "ylim": (0.0, 1.05),
            "vlines": (605.0, 1330.0, 1520.0),
        }],
    )
    save_figure(
        BASELINE_DIR / "00_raw_spectrum.png",
        title="00 BASELINE - raw Eq. 2 spectra",
        subtitle="Absolute values retained in pm/V; the lower panel expands the calculated curves",
        footer="Normalization is not changed here. The paper scale and calculated Eq. 2 scale remain visibly different.",
        panels=[
            {
                "title": "Paper and calculated spectra on the paper amplitude scale",
                "ylabel": "|chi2| (pm/V)",
                "series": [
                    {"label": "Paper Fig. 2d", "x": WAVELENGTHS, "y": paper, "color": COLORS["paper"], "dashed": True},
                    {"label": "Demo 21 parabolic", "x": WAVELENGTHS, "y": np.abs(demo), "color": COLORS["demo"]},
                    {"label": "Hybrid Eq. 2", "x": WAVELENGTHS, "y": np.abs(hybrid), "color": COLORS["hybrid"]},
                ],
                "xlim": (400.0, 1850.0), "ylim": (0.0, 4200.0), "vlines": (605.0, 1330.0, 1520.0),
            },
            {
                "title": "Calculated spectra expanded - same raw values",
                "ylabel": "|chi2| (pm/V)",
                "series": [
                    {"label": "Demo 21 parabolic", "x": WAVELENGTHS, "y": np.abs(demo), "color": COLORS["demo"]},
                    {"label": "Hybrid Eq. 2", "x": WAVELENGTHS, "y": np.abs(hybrid), "color": COLORS["hybrid"]},
                ],
                "xlim": (400.0, 1850.0), "ylim": (0.0, 100.0), "vlines": (605.0, 1330.0, 1520.0),
            },
        ],
    )

    rows = []
    for name, values in (("paper", paper.astype(complex)), ("demo21", demo), ("hybrid", hybrid)):
        norm = normalized_magnitude(values)
        node1_nm, node1_min = window_minimum(norm, NODE1)
        node2_nm, node2_min = window_minimum(norm, NODE2)
        peak_nm, peak_norm = dominant_peak(norm)
        rows.append({
            "model": name,
            "node1_window_nm": "550-650",
            "node1_min_nm": node1_nm,
            "node1_min_normalized": node1_min,
            "node2_window_nm": "1200-1400",
            "node2_min_nm": node2_nm,
            "node2_min_normalized": node2_min,
            "dominant_peak_nm": peak_nm,
            "dominant_peak_normalized": peak_norm,
            "dominant_peak_raw_pm_per_V": float(np.max(np.abs(values))),
            "normalized_rmse_vs_paper": 0.0 if name == "paper" else normalized_rmse(np.abs(values), paper_norm),
        })
    write_csv(BASELINE_DIR / "baseline_metrics.csv", list(rows[0]), rows)

    spectrum_rows = []
    for index, wavelength in enumerate(WAVELENGTHS):
        spectrum_rows.append({
            "wavelength_nm": wavelength,
            "paper_pm_per_V": paper[index],
            "paper_normalized": paper_norm[index],
            "demo21_real_pm_per_V": demo[index].real,
            "demo21_imag_pm_per_V": demo[index].imag,
            "demo21_abs_pm_per_V": abs(demo[index]),
            "demo21_normalized": demo_norm[index],
            "hybrid_real_pm_per_V": hybrid[index].real,
            "hybrid_imag_pm_per_V": hybrid[index].imag,
            "hybrid_abs_pm_per_V": abs(hybrid[index]),
            "hybrid_normalized": hybrid_norm[index],
        })
    write_csv(BASELINE_DIR / "baseline_spectra.csv", list(spectrum_rows[0]), spectrum_rows)


def run_complex(paper: np.ndarray, demo: np.ndarray, hybrid: np.ndarray, metrics: dict[str, object]) -> None:
    paper_norm = paper / float(np.max(paper))
    panels = []
    for label, values in (("Demo 21 parabolic", demo), ("Hybrid non-parabolic", hybrid)):
        bound = float(np.max(np.abs(np.concatenate([values.real, values.imag, np.abs(values)])))) * 1.06
        panels.append({
            "title": label,
            "ylabel": "chi2 (pm/V)",
            "series": [
                {"label": "Re(chi2)", "x": WAVELENGTHS, "y": values.real, "color": COLORS["real"]},
                {"label": "Im(chi2)", "x": WAVELENGTHS, "y": values.imag, "color": COLORS["imag"]},
                {"label": "|chi2|", "x": WAVELENGTHS, "y": np.abs(values), "color": COLORS["abs"], "dashed": True},
            ],
            "xlim": (400.0, 1850.0), "ylim": (-bound, bound), "vlines": (605.0, 1330.0, 1520.0),
        })
    save_figure(
        COMPLEX_DIR / "01_complex_full_spectrum.png",
        title="01 COMPLEX COMPONENTS - signed response and magnitude",
        subtitle="No physics changed: the existing complex susceptibility is exposed before taking magnitude",
        footer="A zero of Re(chi2) is not a zero of |chi2| when Im(chi2) remains finite.",
        panels=panels,
    )

    max_demo_real = float(np.max(np.abs(demo.real)))
    max_hybrid_real = float(np.max(np.abs(hybrid.real)))
    save_figure(
        COMPLEX_DIR / "01_real_vs_paper.png",
        title="01 COMPLEX COMPONENTS - signed real part versus paper",
        subtitle="Signed real curves use max|Re| normalization; the paper digitization is nonnegative and normalized to its maximum",
        footer="Negative regions are preserved. This plot tests whether paper nodes align with real-part sign changes.",
        panels=[{
            "title": "Full spectrum",
            "ylabel": "Signed normalized response",
            "series": [
                {"label": "Paper", "x": WAVELENGTHS, "y": paper_norm, "color": COLORS["paper"], "dashed": True},
                {"label": "Demo 21 Re", "x": WAVELENGTHS, "y": demo.real / max_demo_real, "color": COLORS["demo"]},
                {"label": "Hybrid Re", "x": WAVELENGTHS, "y": hybrid.real / max_hybrid_real, "color": COLORS["hybrid"]},
            ],
            "xlim": (400.0, 1850.0), "ylim": (-1.05, 1.05), "vlines": (605.0, 1330.0, 1520.0),
        }],
    )

    def zoom(path: Path, title: str, window: tuple[float, float]) -> None:
        save_figure(
            path,
            title=title,
            subtitle="Signed Re(chi2) and |chi2| retain a common per-model full-spectrum normalization",
            footer="Vertical line marks the digitized paper node within this window.",
            panels=[
                {
                    "title": "Demo 21 parabolic",
                    "ylabel": "Normalized response",
                    "series": [
                        {"label": "Paper", "x": WAVELENGTHS, "y": paper_norm, "color": COLORS["paper"], "dashed": True},
                        {"label": "Re/max|Re|", "x": WAVELENGTHS, "y": demo.real / max_demo_real, "color": COLORS["real"]},
                        {"label": "|chi2|/max", "x": WAVELENGTHS, "y": normalized_magnitude(demo), "color": COLORS["abs"]},
                    ],
                    "xlim": window, "ylim": (-1.05, 1.05), "vlines": (605.0 if window == (500.0, 700.0) else 1330.0,),
                },
                {
                    "title": "Hybrid non-parabolic",
                    "ylabel": "Normalized response",
                    "series": [
                        {"label": "Paper", "x": WAVELENGTHS, "y": paper_norm, "color": COLORS["paper"], "dashed": True},
                        {"label": "Re/max|Re|", "x": WAVELENGTHS, "y": hybrid.real / max_hybrid_real, "color": COLORS["real"]},
                        {"label": "|chi2|/max", "x": WAVELENGTHS, "y": normalized_magnitude(hybrid), "color": COLORS["abs"]},
                    ],
                    "xlim": window, "ylim": (-1.05, 1.05), "vlines": (605.0 if window == (500.0, 700.0) else 1330.0,),
                },
            ],
        )

    zoom(COMPLEX_DIR / "01_zoom_600nm.png", "01 COMPLEX COMPONENTS - node 1 zoom", (500.0, 700.0))
    zoom(COMPLEX_DIR / "01_zoom_1330nm.png", "01 COMPLEX COMPONENTS - node 2 zoom", (1200.0, 1400.0))

    save_figure(
        COMPLEX_DIR / "01_phase.png",
        title="01 COMPLEX COMPONENTS - susceptibility phase",
        subtitle="Principal complex phase in degrees; discontinuities near +/-180 degrees are plotting wraps",
        footer="Large phase motion can accompany interference, but a true |chi2| node requires both Re and Im to approach zero.",
        panels=[{
            "title": "Phase across the full spectrum",
            "ylabel": "arg(chi2) (degrees)",
            "series": [
                {"label": "Demo 21", "x": WAVELENGTHS, "y": np.degrees(np.angle(demo)), "color": COLORS["phase_demo"]},
                {"label": "Hybrid", "x": WAVELENGTHS, "y": np.degrees(np.angle(hybrid)), "color": COLORS["phase_hybrid"]},
            ],
            "xlim": (400.0, 1850.0), "ylim": (-180.0, 180.0), "vlines": (605.0, 1330.0, 1520.0),
        }],
    )

    rows = []
    for index, wavelength in enumerate(WAVELENGTHS):
        rows.append({
            "wavelength_nm": wavelength,
            "demo21_chi_real_pm_per_V": demo[index].real,
            "demo21_chi_imag_pm_per_V": demo[index].imag,
            "demo21_chi_abs_pm_per_V": abs(demo[index]),
            "demo21_phase_rad": np.angle(demo[index]),
            "demo21_phase_deg": np.degrees(np.angle(demo[index])),
            "hybrid_chi_real_pm_per_V": hybrid[index].real,
            "hybrid_chi_imag_pm_per_V": hybrid[index].imag,
            "hybrid_chi_abs_pm_per_V": abs(hybrid[index]),
            "hybrid_phase_rad": np.angle(hybrid[index]),
            "hybrid_phase_deg": np.degrees(np.angle(hybrid[index])),
        })
    write_csv(COMPLEX_DIR / "complex_components.csv", list(rows[0]), rows)

    metric_rows = []
    for name in ("demo21", "hybrid"):
        record = metrics[name]
        metric_rows.append({
            "model": name,
            "real_crossings_550_650_nm": ";".join(f"{x:.6f}" for x in record["real_crossings_node1"]),
            "real_crossings_1200_1400_nm": ";".join(f"{x:.6f}" for x in record["real_crossings_node2"]),
            "min_abs_real_norm_550_650": record["real_node1"][1],
            "min_abs_real_norm_1200_1400": record["real_node2"][1],
            "min_magnitude_norm_550_650": record["node1"][1],
            "min_magnitude_norm_1200_1400": record["node2"][1],
            "max_phase_step_550_650_deg": record["phase_jump_node1_deg"],
            "max_phase_step_1200_1400_deg": record["phase_jump_node2_deg"],
            "phase_span_550_650_deg": record["phase_span_node1_deg"],
            "phase_span_1200_1400_deg": record["phase_span_node2_deg"],
            "imag_at_first_real_crossing_node1_pm_per_V": record["imag_at_first_real_crossing_node1_pm_per_V"],
            "magnitude_norm_at_first_real_crossing_node1": record["magnitude_norm_at_first_real_crossing_node1"],
            "imag_at_first_real_crossing_node2_pm_per_V": record["imag_at_first_real_crossing_node2_pm_per_V"],
            "magnitude_norm_at_first_real_crossing_node2": record["magnitude_norm_at_first_real_crossing_node2"],
            "normalized_rmse_magnitude_vs_paper": record["shape_rmse_magnitude"],
            "normalized_rmse_abs_real_vs_paper": record["shape_rmse_abs_real"],
        })
    write_csv(COMPLEX_DIR / "complex_metrics.csv", list(metric_rows[0]), metric_rows)


def write_master(metrics: dict[str, object]) -> None:
    paper_node1_nm, paper_node1_min = metrics["paper_node1"]
    paper_node2_nm, paper_node2_min = metrics["paper_node2"]
    rows = []
    for debug_id, debug_name, model, use_real in (
        ("00a", "baseline_demo21_magnitude", "demo21", False),
        ("00b", "baseline_hybrid_magnitude", "hybrid", False),
        ("01a", "demo21_real_component", "demo21", True),
        ("01b", "hybrid_real_component", "hybrid", True),
    ):
        record = metrics[model]
        node1 = record["real_node1"] if use_real else record["node1"]
        node2 = record["real_node2"] if use_real else record["node2"]
        crossings = record["real_crossings_node1"] + record["real_crossings_node2"]
        shape_error = record["shape_rmse_abs_real"] if use_real else record["shape_rmse_magnitude"]
        interpretation = (
            "Signed real-part diagnostic; zero crossings do not imply a magnitude node when Im remains finite."
            if use_real
            else "Frozen solver-free baseline using cached licensed Demo 21 Case 04 states."
        )
        rows.append({
            "debug_id": debug_id,
            "debug_name": debug_name,
            "model": model,
            "hypothesis": "Paper may show a signed component." if use_real else "Freeze current spectral shape.",
            "paper_node1_nm": paper_node1_nm,
            "baseline_node1_nm": record["node1"][0],
            "new_node1_nm": node1[0],
            "paper_node1_min_norm": paper_node1_min,
            "baseline_node1_min_norm": record["node1"][1],
            "new_node1_min_norm": node1[1],
            "paper_node2_nm": paper_node2_nm,
            "baseline_node2_nm": record["node2"][0],
            "new_node2_nm": node2[0],
            "paper_node2_min_norm": paper_node2_min,
            "baseline_node2_min_norm": record["node2"][1],
            "new_node2_min_norm": node2[1],
            "dominant_peak_nm": record["dominant_peak"][0],
            "shape_error_metric_normalized_rmse": shape_error,
            "creates_sign_change": bool(crossings) if use_real else False,
            "improves_paper_agreement": (
                shape_error < record["shape_rmse_magnitude"] if use_real else False
            ),
            "interpretation": interpretation,
        })
    write_csv(MASTER, list(rows[0]), rows)


def main() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    COMPLEX_DIR.mkdir(parents=True, exist_ok=True)
    paper, demo, hybrid = reproduce_spectra()
    metrics = phase1_metrics(paper, demo, hybrid)
    run_baseline(paper, demo, hybrid, metrics)
    run_complex(paper, demo, hybrid, metrics)
    write_master(metrics)
    (OUT / "phase1_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Outputs: {OUT}")


if __name__ == "__main__":
    main()
