#!/usr/bin/env python3
"""Regenerate the README tables (between the TABLES markers) and the charts in images/."""
from __future__ import annotations

import math
import pathlib
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dishcalc as dc

ROOT = pathlib.Path(__file__).parent
DISHES = [("23.6 in", 23.6 * dc.INCH), ("24 in", 24 * dc.INCH), ("0.75 m", 0.75),
          ("0.80 m", 0.80), ("0.88 m", 0.88)]
BANDS = [10.368, 24.192]
EFFS = [0.55, 0.60, 0.65, 0.70, 0.75]
RMS = [0.25, 0.5, 0.75, 1.0]

# Reference palette (validated categorical order) and text/surface tokens.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def gain_table(f: float) -> str:
    head = "| Dish | " + " | ".join(f"{e:.0%}" for e in EFFS) + " | HPBW |\n"
    head += "|---|" + "---|" * (len(EFFS) + 1) + "\n"
    rows = []
    for name, d in DISHES:
        g = " | ".join(f"{dc.gain_dbi(d, f, e):.2f}" for e in EFFS)
        rows.append(f"| {name} ({d:.3f} m) | {g} | {dc.hpbw_deg(d, f):.2f}° |")
    return head + "\n".join(rows)


def ruze_table() -> str:
    t = "| RMS surface error | " + " | ".join(f"{f} GHz" for f in BANDS) + " |\n|---|" + "---|" * len(BANDS) + "\n"
    t += "\n".join(f"| {r} mm | " + " | ".join(f"{dc.ruze_loss_db(r, f):.2f} dB" for f in BANDS) + " |" for r in RMS)
    return t


def tolerance_table() -> str:
    t = "| Max loss accepted | " + " | ".join(f"RMS allowed @ {f} GHz" for f in BANDS) + " |\n|---|" + "---|" * len(BANDS) + "\n"
    t += "\n".join(f"| {l} dB | " + " | ".join(f"{dc.rms_for_loss_mm(l, f):.2f} mm" for f in BANDS) + " |"
                   for l in (0.25, 0.5, 1, 3))
    return t


def feed_table() -> str:
    t = "| Case | Illumination × spillover efficiency |\n|---|---|\n"
    n4, e4 = dc.best_feed_n(0.40)
    n31, e31 = dc.best_feed_n(0.31)
    t += f"| f/D 0.40 feed (cos^{n4:.2f}) on f/D 0.40 dish | {e4:.1%} |\n"
    t += f"| Same feed on f/D 0.31 dish | {dc.illumination_efficiency(n4, 0.31):.1%} |\n"
    t += f"| Feed optimized for f/D 0.31 (cos^{n31:.2f}) | {e31:.1%} |\n"
    same = 10 * math.log10(e4 / dc.illumination_efficiency(n4, 0.31))
    t += (f"\nThe 0.40 feed loses **{same:.2f} dB** on the 0.31 dish compared with its own 0.40 dish, "
          f"and **{dc.feed_mismatch_loss_db(0.31, 0.40):.2f} dB** compared with the best feed for f/D 0.31. ")
    t += (f"Rim half-angle is {dc.rim_half_angle_deg(0.31):.1f}° at f/D 0.31 vs "
          f"{dc.rim_half_angle_deg(0.40):.1f}° at f/D 0.40.")
    return t


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)


def chart_loss_vs_rms():
    eps = np.linspace(0, 1.5, 151)
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for f, color, label in ((10.368, BLUE, "10.368 GHz"), (24.192, ORANGE, "24.192 GHz")):
        y = [dc.ruze_loss_db(e, f) for e in eps]
        ax.plot(eps, y, color=color, linewidth=2, label=label)
        ax.annotate(label, (eps[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=10)
    ax.axhline(1.0, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.02, 1.12, "1 dB", color=INK2, fontsize=9)
    style(ax, "Gain lost to dish surface error (Ruze)", "RMS surface error (mm)", "Gain loss (dB)")
    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 10.5)
    ax.legend(frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.subplots_adjust(right=0.86)
    fig.savefig(ROOT / "images" / "ruze_loss_vs_rms.png", dpi=150)
    plt.close(fig)


def chart_loss_vs_freq():
    f = np.linspace(2, 30, 281)
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for r, color in zip(RMS, (BLUE, ORANGE, AQUA, YELLOW)):
        ax.plot(f, [dc.ruze_loss_db(r, x) for x in f], color=color, linewidth=2, label=f"{r} mm RMS")
    for band in BANDS:
        ax.axvline(band, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(band + 0.25, 6.6, f"{band} GHz", color=INK2, fontsize=9)
    style(ax, "Surface-error loss vs. frequency", "Frequency (GHz)", "Gain loss (dB)")
    ax.set_xlim(2, 30)
    ax.set_ylim(0, 7)
    ax.legend(frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "ruze_loss_vs_freq.png", dpi=150)
    plt.close(fig)


EFF_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]  # ordinal blue, 55 -> 75 %


def chart_gain_vs_diameter(f: float, fname: str, ylim: tuple[float, float]):
    d = np.linspace(0.5, 1.0, 201)
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for eff, color in zip(EFFS, EFF_RAMP):
        y = [dc.gain_dbi(x, f, eff) for x in d]
        ax.plot(d, y, color=color, linewidth=2, label=f"{eff:.0%}")
        ax.annotate(f"{eff:.0%}", (d[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=9)
    for name, dia in DISHES:
        ax.axvline(dia, color=GRID, linewidth=1, zorder=0)
        g = [dc.gain_dbi(dia, f, e) for e in EFFS]
        ax.plot([dia] * len(EFFS), g, "o", color=INK2, markersize=4, zorder=3)
    labels = {"23.6 in": (0.588, "left"), "24 in": (0.621, "right"), "0.75 m": (0.75, "center"),
              "0.80 m": (0.80, "center"), "0.88 m": (0.88, "center")}
    for name, dia in DISHES:
        x, ha = labels[name]
        ax.text(x, ylim[0] + 0.25, name, color=INK2, fontsize=8.5,
                ha={"left": "right", "right": "left", "center": "center"}[ha])
    style(ax, f"Dish gain vs. diameter at {f} GHz", "Aperture diameter (m)", "Gain (dBi)")
    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(*ylim)
    ax.legend(title="Aperture efficiency", frameon=False, loc="upper left", labelcolor=INK,
              fontsize=9, title_fontsize=9)
    fig.tight_layout()
    fig.subplots_adjust(right=0.9)
    fig.savefig(ROOT / "images" / fname, dpi=150)
    plt.close(fig)


FD = np.round(np.arange(0.30, 1.001, 0.01), 3)


def chart_illum_vs_fd():
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for design, color in zip((0.30, 0.40, 0.60, 0.80), (BLUE, ORANGE, AQUA, YELLOW)):
        n, _ = dc.best_feed_n(design)
        y = [dc.illumination_efficiency(n, fd) * 100 for fd in FD]
        ax.plot(FD, y, color=color, linewidth=2, label=f"Feed for f/D {design:.2f} (cos^{n:.1f})")
        ax.plot([design], [dc.illumination_efficiency(n, design) * 100], "o", color=color,
                markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    env = [dc.best_feed_n(fd)[1] * 100 for fd in FD]
    ax.plot(FD, env, color=INK2, linewidth=1.2, linestyle=(0, (4, 3)), label="Best cos^n feed at each f/D")
    style(ax, "Prime-focus dishes: illumination × spillover vs. f/D (same on every band)",
          "Prime-focus dish f/D", "Efficiency (%)")
    ax.set_xlim(0.30, 1.0)
    ax.set_ylim(40, 90)
    ax.legend(frameon=False, loc="lower right", labelcolor=INK, fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "illumination_vs_fd.png", dpi=150)
    plt.close(fig)


def chart_net_eff_by_band():
    eps = np.linspace(0, 1.2, 121)
    illum = dc.best_feed_n(0.40)[1]
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    ax.axhline(illum * 100, color=INK2, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(0.01, illum * 100 + 1.2, f"Perfect surface: {illum:.1%} (any band)", color=INK2, fontsize=9)
    for f, color in ((10.368, BLUE), (24.192, ORANGE)):
        y = [illum * 10 ** (-dc.ruze_loss_db(e, f) / 10) * 100 for e in eps]
        ax.plot(eps, y, color=color, linewidth=2, label=f"{f} GHz")
        ax.annotate(f"{f} GHz", (eps[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=10)
    style(ax, "Illumination efficiency by band as the surface degrades",
          "RMS surface error (mm)", "Illumination × spillover × surface (%)")
    ax.set_xlim(0, 1.2)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower left", labelcolor=INK)
    fig.tight_layout()
    fig.subplots_adjust(right=0.86)
    fig.savefig(ROOT / "images" / "efficiency_by_band.png", dpi=150)
    plt.close(fig)


# Offset vs prime-focus planning scenarios. Surface RMS values and OTHER_LOSS_DB are
# ASSUMPTIONS for illustration -- edit them to match dishes you have measured.
SCEN_D = 0.75            # dish diameter, m
FEED_BLOCK_WL = 3.0      # prime-focus feed shadow diameter, in wavelengths
OTHER_LOSS_DB = 0.7      # phase error, cross-pol, feed loss, struts (lumped)
SCENARIOS = [
    # name, geometry, dish f/D, feed designed for f/D, RMS mm
    ("Offset TV dish, pressed steel, stock-style feed", "offset", 0.70, 0.70, 0.60),
    ("Prime focus, spun aluminum, f/D 0.40, matched feed", "prime", 0.40, 0.40, 0.25),
    ("Prime focus, spun aluminum, f/D 0.31, feed for 0.40", "prime", 0.31, 0.40, 0.25),
    ("Prime focus, spun aluminum, f/D 0.31, deep-dish feed", "prime", 0.31, 0.31, 0.25),
    ("Prime focus, mesh/homebrew, f/D 0.45, matched feed", "prime", 0.45, 0.45, 1.00),
    # Optional 6th field: per-band feed efficiency (10, 24) from published data instead of the cos^n model.
    ("Offset TV dish, pressed steel, W1GHZ dual-band feed (Chaparral horn)", "offset", 0.70, 0.70, 0.60,
     (0.74, 0.76)),
]


def scenario_rows():
    """[(name, rms, illum, (eff10, gain10), (eff24, gain24), (blk10, blk24)), ...]"""
    other = 10 ** (-OTHER_LOSS_DB / 10)
    rows = []
    for name, geom, fd, feed_fd, rms, *override in SCENARIOS:
        n, _ = dc.best_feed_n(feed_fd)
        model_illum = dc.illumination_efficiency(n, fd)
        cells, blocks = [], []
        for k, f in enumerate(BANDS):
            illum = override[0][k] if override else model_illum
            blk = 1.0 if geom == "offset" else dc.blockage_efficiency(FEED_BLOCK_WL * dc.wavelength_m(f), SCEN_D)
            blocks.append(blk)
            eff = illum * blk * other * 10 ** (-dc.ruze_loss_db(rms, f) / 10)
            cells.append((eff, dc.gain_dbi(SCEN_D, f, eff)))
        illum_txt = f"{override[0][0]:.0%} / {override[0][1]:.0%}*" if override else f"{model_illum:.1%}"
        rows.append((name, rms, illum_txt, cells[0], cells[1], tuple(blocks)))
    return rows


def scenario_table() -> str:
    t = ("| Dish | RMS (assumed) | Illum. × spill | Blockage 10 / 24 | Net eff. 10 GHz | Net eff. 24 GHz "
         "| Gain 10.368 | Gain 24.192 |\n|---|---|---|---|---|---|---|---|\n")
    for name, rms, illum, c10, c24, blk in scenario_rows():
        t += (f"| {name} | {rms:.2f} mm | {illum} | {blk[0]:.1%} / {blk[1]:.1%} | "
              f"{c10[0]:.1%} | {c24[0]:.1%} | {c10[1]:.2f} | {c24[1]:.2f} |\n")
    t += (f"\nAll rows: {SCEN_D} m aperture, {OTHER_LOSS_DB} dB lumped for phase error, cross-pol, feed loss "
          f"and struts, feed shadow {FEED_BLOCK_WL:.0f}λ across. Gains in dBi. "
          "\\* W1GHZ's calculated 10 / 24 GHz efficiency at f/D 0.7 (includes phase error), used instead of the "
          "cos^n model.")
    return t


def efficiency_band_table() -> str:
    cols = [(f, r) for f in BANDS for r in (0.5, 1.0)]
    t = "| Dish f/D | Ideal (any band) | " + " | ".join(f"{f} GHz @ {r} mm" for f, r in cols) + " |\n"
    t += "|---|---|" + "---|" * len(cols) + "\n"
    for fd in (0.35, 0.40, 0.50, 0.60, 0.80):
        e = dc.best_feed_n(fd)[1]
        t += f"| {fd:.2f} | {e:.1%} | " + " | ".join(f"{dc.net_efficiency(fd, f, r):.1%}" for f, r in cols) + " |\n"
    return t.rstrip()


def chart_tolerance():
    budgets = [0.25, 0.5, 1.0, 3.0]
    x = np.arange(len(budgets))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for i, (f, color) in enumerate(((BANDS[0], BLUE), (BANDS[1], ORANGE))):
        vals = [dc.rms_for_loss_mm(b, f) for b in budgets]
        bars = ax.bar(x + (i - 0.5) * (w + 0.02), vals, w, color=color, label=f"{f} GHz", zorder=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.2f}", ha="center", color=INK, fontsize=9)
    style(ax, "Largest RMS surface error for a given loss budget", "Surface-error loss you'll accept",
          "RMS surface error allowed (mm)")
    ax.set_xticks(x, [f"{b:g} dB" for b in budgets])
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 2.15)
    ax.legend(frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "surface_tolerance.png", dpi=150)
    plt.close(fig)


def chart_feed_mismatch():
    fd = np.round(np.arange(0.30, 0.801, 0.01), 3)
    best = {x: dc.best_feed_n(x)[1] for x in fd}
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for design, color in zip((0.31, 0.40, 0.50, 0.60), (BLUE, ORANGE, AQUA, YELLOW)):
        n, _ = dc.best_feed_n(design)
        y = [10 * math.log10(best[x] / dc.illumination_efficiency(n, x)) for x in fd]
        ax.plot(fd, y, color=color, linewidth=2, label=f"Feed designed for f/D {design:.2f}")
    ax.axhline(0.5, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.445, 0.40, "0.5 dB", color=INK2, fontsize=9)
    ax.plot([0.31], [10 * math.log10(best[0.31] / dc.illumination_efficiency(dc.best_feed_n(0.40)[0], 0.31))],
            "o", color=ORANGE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    style(ax, "Prime focus: loss from a feed not matched to the dish (any band)",
          "Prime-focus dish f/D", "Loss vs. best feed for that dish (dB)")
    ax.set_xlim(0.30, 0.80)
    ax.set_ylim(0, 3)
    ax.legend(frameon=False, loc="upper right", labelcolor=INK, fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "feed_mismatch.png", dpi=150)
    plt.close(fig)


def chart_scenarios():
    rows = scenario_rows()
    names = [r[0] for r in rows][::-1]
    y = np.arange(len(names))
    h = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.6), facecolor=SURFACE)
    for i, (f, color) in enumerate(((BANDS[0], BLUE), (BANDS[1], ORANGE))):
        effs = [r[3 + i][0] * 100 for r in rows][::-1]
        gains = [r[3 + i][1] for r in rows][::-1]
        bars = ax.barh(y + (0.5 - i) * (h + 0.02), effs, h, color=color, label=f"{f} GHz", zorder=2)
        for b, e, g in zip(bars, effs, gains):
            ax.text(e + 0.8, b.get_y() + b.get_height() / 2, f"{e:.0f}%  ({g:.1f} dBi)", va="center",
                    color=INK, fontsize=8.5)
    style(ax, f"Offset vs. prime focus: net efficiency of a {SCEN_D} m dish", "Net aperture efficiency (%)", "")
    ax.set_yticks(y, [n.replace(", ", ",\n", 1) for n in names], fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 92)
    ax.legend(frameon=False, loc="lower right", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "offset_vs_prime_focus.png", dpi=150)
    plt.close(fig)


def chart_size_vs_surface():
    d = np.linspace(0.5, 1.0, 201)
    base = 0.60
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.0), facecolor=SURFACE, sharey=False)
    for ax, f in zip(axes, BANDS):
        for rms, color in zip(RMS, (BLUE, ORANGE, AQUA, YELLOW)):
            loss = dc.ruze_loss_db(rms, f)
            ax.plot(d, [dc.gain_dbi(x, f, base) - loss for x in d], color=color, linewidth=2,
                    label=f"{rms} mm RMS")
        lo = dc.gain_dbi(0.5, f, base) - dc.ruze_loss_db(1.0, f)
        style(ax, f"{f} GHz", "Aperture diameter (m)", "Net gain (dBi)")
        ax.set_xlim(0.5, 1.0)
        top = dc.gain_dbi(1.0, f, base) + 0.5
        ax.set_ylim(top - 11, top)
        ax.title.set_fontsize(12)
    axes[0].legend(frameon=False, loc="lower right", labelcolor=INK, fontsize=9)
    fig.suptitle(f"Size vs. surface: net gain at {base:.0%} efficiency before surface loss",
                 x=0.01, ha="left", color=INK, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "size_vs_surface.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- dual-band (W1GHZ feed)

REAL_WORLD = 0.85   # W1GHZ: "REAL WORLD at least 15% lower" than calculated efficiency
DUAL_HORN = "Chaparral"
DUAL_DISHES = [("18 in", 18 * dc.INCH)] + DISHES
DUAL_RMS = [0.25, 0.5, 0.75]


def load_horns():
    import csv
    with open(ROOT / "data" / "w1ghz_dualband_2004.csv") as fh:
        rows = [r for r in csv.DictReader(line for line in fh if not line.startswith("#"))]
    for r in rows:
        for k in r:
            if k != "horn":
                r[k] = float(r[k])
    return rows


def horn_table() -> str:
    t = ("| Horn | 24 GHz best eff. (f/D) | 10 GHz best eff. (f/D) | Eff. at f/D 0.7: 24 GHz | "
         "Eff. at f/D 0.7: 10 GHz | 10 vs 24 GHz | Phase-center gap |\n|---|---|---|---|---|---|---|\n")
    for h in load_horns():
        gap = abs(h["pc24_mm"] - h["pc10_mm"])
        diff = 10 * math.log10(h["offset07_eff10"] / h["offset07_eff24"])
        lam24 = dc.wavelength_m(BANDS[1]) * 1000
        lam10 = dc.wavelength_m(BANDS[0]) * 1000
        name = f"**{h['horn']}**" if h["horn"] == DUAL_HORN else h["horn"]
        t += (f"| {name} | {h['eff24_best']:.0%} ({h['fd24_best']:.2f}) | {h['eff10_best']:.0%} ({h['fd10_best']:.2f}) | "
              f"{h['offset07_eff24']:.0%} | {h['offset07_eff10']:.0%} | {diff:+.2f} dB | "
              f"{gap:.1f} mm ({gap / lam10:.2f} λ / {gap / lam24:.2f} λ) |\n")
    t += ("\nCalculated (HFSS) values from W1GHZ (2004); see `data/w1ghz_dualband_2004.csv`. "
          "\"10 vs 24 GHz\" is the 10 GHz efficiency relative to 24 GHz at offset f/D 0.7, "
          "with the feed at the 24 GHz phase center. The phase-center gap is shown in wavelengths at 10 and at 24 GHz.")
    return t


def dual_effs():
    h = next(x for x in load_horns() if x["horn"] == DUAL_HORN)
    return h["offset07_eff10"] * REAL_WORLD, h["offset07_eff24"] * REAL_WORLD


def dual_gain_table() -> str:
    e10, e24 = dual_effs()
    cols = [(f, e, r) for f, e in ((BANDS[0], e10), (BANDS[1], e24)) for r in DUAL_RMS]
    t = "| Dish | " + " | ".join(f"{'10' if f < 20 else '24'} GHz @ {r} mm" for f, _, r in cols) + " |\n"
    t += "|---|" + "---|" * len(cols) + "\n"
    for name, d in DUAL_DISHES:
        t += f"| {name} ({d:.3f} m) | " + " | ".join(
            f"{dc.gain_dbi(d, f, e) - dc.ruze_loss_db(r, f):.1f}" for f, e, r in cols) + " |\n"
    t += (f"\nNet gain in dBi with the {DUAL_HORN} horn: W1GHZ's calculated efficiency at f/D 0.7 "
          f"× {REAL_WORLD} real-world factor = {e10:.1%} at 10.368 GHz and {e24:.1%} at 24.192 GHz, "
          "minus Ruze surface loss.")
    return t


def chart_horns():
    horns = load_horns()
    names = [h["horn"].replace(" (bare dual-mode)", "\n(bare)").replace(" corrugated", "\ncorrugated") for h in horns]
    x = np.arange(len(horns))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    for i, (key, f, color) in enumerate((("offset07_eff10", BANDS[0], BLUE), ("offset07_eff24", BANDS[1], ORANGE))):
        vals = [h[key] * 100 for h in horns]
        bars = ax.bar(x + (i - 0.5) * (w + 0.02), vals, w, color=color, label=f"{f} GHz", zorder=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", color=INK, fontsize=9)
    style(ax, "W1GHZ dual-band feed: calculated efficiency at offset f/D 0.7, by horn",
          "", "Calculated efficiency (%)")
    ax.set_xticks(x, names, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 95)
    ax.legend(frameon=False, loc="upper right", labelcolor=INK, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "dualband_horns.png", dpi=150)
    plt.close(fig)


def chart_dual_gain():
    e10, e24 = dual_effs()
    d = np.linspace(0.4, 1.0, 241)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.0), facecolor=SURFACE)
    for ax, f, e in zip(axes, BANDS, (e10, e24)):
        for rms, color in zip(DUAL_RMS, (BLUE, ORANGE, AQUA)):
            ax.plot(d, [dc.gain_dbi(x, f, e) - dc.ruze_loss_db(rms, f) for x in d], color=color, linewidth=2,
                    label=f"{rms} mm RMS")
        for name, dia in DUAL_DISHES:
            ax.axvline(dia, color=GRID, linewidth=1, zorder=0)
        style(ax, f"{f} GHz ({e:.0%} before surface loss)", "Aperture diameter (m)", "Net gain (dBi)")
        ax.title.set_fontsize(12)
        ax.set_xlim(0.4, 1.0)
        top = dc.gain_dbi(1.0, f, e) + 0.5
        ax.set_ylim(top - 11, top)
    axes[0].legend(frameon=False, loc="lower right", labelcolor=INK, fontsize=9)
    fig.suptitle(f"Offset dish with the W1GHZ dual-band feed ({DUAL_HORN} horn): net gain",
                 x=0.01, ha="left", color=INK, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "dualband_gain.png", dpi=150)
    plt.close(fig)


def main():
    chart_loss_vs_rms()
    chart_loss_vs_freq()
    chart_illum_vs_fd()
    chart_gain_vs_diameter(10.368, "gain_vs_diameter_10ghz.png", (31.5, 40.0))
    chart_gain_vs_diameter(24.192, "gain_vs_diameter_24ghz.png", (39.0, 47.5))
    chart_tolerance()
    chart_feed_mismatch()
    chart_scenarios()
    chart_size_vs_surface()
    chart_horns()
    chart_dual_gain()
    chart_net_eff_by_band()
    tables = (
        "### 10 GHz (10.368 GHz, λ = {:.2f} mm) — gain in dBi\n\n{}\n\n"
        "At 10.4 GHz add about 0.03 dB.\n\n"
        "![Gain vs diameter at 10.368 GHz](images/gain_vs_diameter_10ghz.png)\n\n"
        "### 24 GHz (24.192 GHz, λ = {:.2f} mm) — gain in dBi\n\n{}\n\n"
        "![Gain vs diameter at 24.192 GHz](images/gain_vs_diameter_24ghz.png)\n\n"
        "### Surface-error (Ruze) loss\n\n{}\n\n"
        "![Surface-error loss vs frequency](images/ruze_loss_vs_freq.png)\n\n"
        "### Surface tolerance for a given loss budget\n\n{}\n\n"
        "![Surface tolerance by band](images/surface_tolerance.png)\n\n"
        "### Illumination efficiency by band (prime focus, best-matched feed)\n\n{}\n\n"
        "![Illumination efficiency by band](images/efficiency_by_band.png)\n\n"
        "### Feed f/D mismatch example (prime focus: feed for f/D 0.40 on an f/D 0.31 dish)\n\n{}\n\n"
        "![Feed mismatch loss vs f/D](images/feed_mismatch.png)\n\nThe dot marks the f/D 0.40 feed on the f/D 0.31 dish from the table.\n\n"
        "### Offset vs. prime focus: planning comparison\n\n{}\n\n"
        "![Offset vs prime focus net efficiency](images/offset_vs_prime_focus.png)"
    ).format(dc.wavelength_m(10.368) * 1000, gain_table(10.368),
             dc.wavelength_m(24.192) * 1000, gain_table(24.192),
             ruze_table(), tolerance_table(), efficiency_band_table(), feed_table(), scenario_table())
    readme = ROOT / "README.md"
    text = readme.read_text()
    dualband = (
        "#### The W1GHZ feed with different horns\n\n{}\n\n"
        "![Dual-band horn efficiencies](images/dualband_horns.png)\n\n"
        "#### Expected net gain on offset dishes\n\n{}\n\n"
        "![Dual-band net gain](images/dualband_gain.png)"
    ).format(horn_table(), dual_gain_table())
    for tag, body in (("TABLES", tables), ("DUALBAND", dualband)):
        text = re.sub(rf"(<!-- {tag}:START -->\n).*?(<!-- {tag}:END -->)",
                      lambda mm: mm.group(1) + body + "\n" + mm.group(2), text, flags=re.S)
    readme.write_text(text)
    print("README tables and images/ regenerated")


if __name__ == "__main__":
    main()
