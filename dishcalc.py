#!/usr/bin/env python3
"""dishcalc - parabolic dish gain, beamwidth, surface-error and feed-mismatch math.

Every function takes SI-friendly inputs: diameters in metres, frequencies in GHz,
surface error in millimetres. Efficiencies are fractions (0.65 for 65 %).

Run ``python dishcalc.py --help`` for the command-line calculator.
"""
from __future__ import annotations

import argparse
import math

import numpy as np

C = 299_792_458.0  # speed of light, m/s
INCH = 0.0254      # metres per inch


def wavelength_m(freq_ghz: float) -> float:
    """Free-space wavelength in metres."""
    return C / (freq_ghz * 1e9)


def gain_dbi(diameter_m: float, freq_ghz: float, efficiency: float) -> float:
    """Dish gain in dBi: G = eta * (pi * D / lambda)^2.

    Efficiency multiplies the gain once; it is *not* inside the square.
    """
    if not 0 < efficiency <= 1:
        raise ValueError("efficiency must be a fraction in (0, 1]")
    lam = wavelength_m(freq_ghz)
    return 10 * math.log10(efficiency * (math.pi * diameter_m / lam) ** 2)


def hpbw_deg(diameter_m: float, freq_ghz: float, k: float = 70.0) -> float:
    """Approximate half-power beamwidth in degrees (k * lambda / D, k ~ 70)."""
    return k * wavelength_m(freq_ghz) / diameter_m


def ruze_loss_db(rms_mm: float, freq_ghz: float) -> float:
    """Gain lost to random RMS surface error (Ruze): 4.343 * (4*pi*eps/lambda)^2."""
    lam_mm = wavelength_m(freq_ghz) * 1000
    return 10 * math.log10(math.e) * (4 * math.pi * rms_mm / lam_mm) ** 2


def rms_for_loss_mm(loss_db: float, freq_ghz: float) -> float:
    """Largest RMS surface error (mm) that keeps Ruze loss at or below loss_db."""
    lam_mm = wavelength_m(freq_ghz) * 1000
    return math.sqrt(loss_db / (10 * math.log10(math.e))) * lam_mm / (4 * math.pi)


# --- Feed illumination (prime-focus geometry, cos^n feed model) -------------

def rim_half_angle_deg(f_over_d: float) -> float:
    """Half-angle from the focus to the dish rim, degrees."""
    return math.degrees(2 * math.atan(1 / (4 * f_over_d)))


def illumination_efficiency(n, f_over_d: float, steps: int = 2000):
    """Combined illumination (taper) x spillover efficiency for a cos^n feed.

    Ideal prime-focus feed: no phase error, cross-pol or blockage (Silver/Kraus
    integral). ``n`` may be a scalar or a numpy array. The result depends only on
    geometry, so a feed scaled to each band gives the same value on every band.
    """
    psi0 = 2 * math.atan(1 / (4 * f_over_d))
    psi = (np.arange(steps) + 0.5) * psi0 / steps
    n_arr = np.atleast_1d(np.asarray(n, dtype=float))[:, None]
    integrand = np.sqrt(2 * (n_arr + 1) * np.cos(psi) ** n_arr) * np.tan(psi / 2)
    eff = (1 / math.tan(psi0 / 2)) ** 2 * (integrand.sum(axis=1) * psi0 / steps) ** 2
    return float(eff[0]) if np.ndim(n) == 0 else eff


_N_GRID = np.arange(0.5, 30.0, 0.05)  # practical feed patterns


def best_feed_n(f_over_d: float) -> tuple[float, float]:
    """(n, efficiency) of the cos^n feed that maximizes efficiency for f_over_d."""
    effs = illumination_efficiency(_N_GRID, f_over_d)
    i = int(np.argmax(effs))
    return float(_N_GRID[i]), float(effs[i])


def net_efficiency(f_over_d: float, freq_ghz: float, rms_mm: float, n: float | None = None) -> float:
    """Illumination x spillover efficiency times the Ruze surface factor.

    Uses the best cos^n feed for f_over_d unless a feed exponent ``n`` is given.
    Excludes blockage, feed loss and phase-center error.
    """
    eff = best_feed_n(f_over_d)[1] if n is None else illumination_efficiency(n, f_over_d)
    return eff * 10 ** (-ruze_loss_db(rms_mm, freq_ghz) / 10)


def blockage_efficiency(block_diameter_m: float, diameter_m: float) -> float:
    """Central-blockage efficiency for a prime-focus dish: (1 - (Db/D)^2)^2.

    Counts the feed/horn shadow only (no struts). Offset dishes have ~no blockage: use 1.0.
    A feed scaled to the band is smaller at higher frequency, so blockage costs less there.
    """
    return (1 - (block_diameter_m / diameter_m) ** 2) ** 2


def feed_mismatch_loss_db(dish_fd: float, feed_designed_fd: float) -> float:
    """Loss (dB) of a feed optimized for feed_designed_fd, used on a dish_fd dish,
    compared with the best cos^n feed for that dish."""
    n, _ = best_feed_n(feed_designed_fd)
    _, eff_dish_best = best_feed_n(dish_fd)
    return 10 * math.log10(eff_dish_best / illumination_efficiency(n, dish_fd))


def _parse_diameter(text: str) -> float:
    """Accept '0.8', '0.8m', '24in', '24"' -> metres."""
    t = text.strip().lower().replace('"', "in")
    if t.endswith("in"):
        return float(t[:-2]) * INCH
    if t.endswith("cm"):
        return float(t[:-2]) / 100
    if t.endswith("m"):
        return float(t[:-1])
    return float(t)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Parabolic dish gain / surface / feed calculator")
    p.add_argument("-d", "--diameter", required=True, type=_parse_diameter,
                   help="dish diameter: 0.8, 0.8m, 76cm or 24in (offset dish: use the width)")
    p.add_argument("-f", "--freq", required=True, type=float, nargs="+", help="frequency in GHz (one or more)")
    p.add_argument("-e", "--eff", type=float, default=0.60, help="aperture efficiency, fraction (default 0.60)")
    p.add_argument("-r", "--rms", type=float, default=0.0, help="RMS surface error in mm (default 0)")
    p.add_argument("--dish-fd", type=float, help="dish f/D, for feed-mismatch loss")
    p.add_argument("--feed-fd", type=float, help="f/D the feed was designed for")
    a = p.parse_args(argv)

    print(f"Dish diameter: {a.diameter:.4f} m ({a.diameter / INCH:.1f} in), efficiency {a.eff:.0%}, "
          f"RMS surface error {a.rms} mm")
    print(f"{'GHz':>8} {'lambda mm':>10} {'gain dBi':>9} {'Ruze dB':>8} {'net dBi':>8} {'HPBW deg':>9}")
    for f in a.freq:
        g = gain_dbi(a.diameter, f, a.eff)
        r = ruze_loss_db(a.rms, f)
        print(f"{f:8.3f} {wavelength_m(f) * 1000:10.2f} {g:9.2f} {r:8.2f} {g - r:8.2f} {hpbw_deg(a.diameter, f):9.2f}")

    if a.dish_fd and a.feed_fd:
        loss = feed_mismatch_loss_db(a.dish_fd, a.feed_fd)
        print(f"\nFeed designed for f/D {a.feed_fd} on an f/D {a.dish_fd} dish: "
              f"~{loss:.2f} dB below the best feed for that dish (ideal cos^n model)")


if __name__ == "__main__":
    main()
