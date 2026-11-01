import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dishcalc as dc  # noqa: E402


def test_gain_24in_10368_70pct():
    assert math.isclose(dc.gain_dbi(24 * dc.INCH, 10.368, 0.70), 34.87, abs_tol=0.01)


def test_gain_088m_104_75pct():
    assert math.isclose(dc.gain_dbi(0.88, 10.4, 0.75), 38.39, abs_tol=0.01)


def test_efficiency_not_squared():
    # Halving efficiency must cost exactly 3.01 dB, not 6.02 dB.
    diff = dc.gain_dbi(0.8, 10.368, 0.8) - dc.gain_dbi(0.8, 10.368, 0.4)
    assert math.isclose(diff, 10 * math.log10(2), abs_tol=1e-9)


def test_band_scaling():
    diff = dc.gain_dbi(0.75, 24.192, 0.6) - dc.gain_dbi(0.75, 10.368, 0.6)
    assert math.isclose(diff, 20 * math.log10(24.192 / 10.368), abs_tol=1e-9)


def test_ruze():
    assert math.isclose(dc.ruze_loss_db(0.5, 24.192), 1.12, abs_tol=0.01)
    assert math.isclose(dc.ruze_loss_db(0.5, 10.368), 0.21, abs_tol=0.01)
    assert math.isclose(dc.ruze_loss_db(dc.rms_for_loss_mm(1.0, 24.192), 24.192), 1.0, abs_tol=1e-9)


def test_feed_mismatch():
    assert 0.5 < dc.feed_mismatch_loss_db(0.31, 0.40) < 0.65
    assert math.isclose(dc.rim_half_angle_deg(0.25), 90.0, abs_tol=1e-9)


def test_parse_diameter():
    assert math.isclose(dc._parse_diameter("24in"), 0.6096)
    assert math.isclose(dc._parse_diameter('24"'), 0.6096)
    assert math.isclose(dc._parse_diameter("76cm"), 0.76)
    assert dc._parse_diameter("0.8m") == 0.8


def test_illumination_band_independent_and_net_by_band():
    # Ideal illumination efficiency is pure geometry: textbook ~82-83 % for cos^2 at f/D 0.4.
    assert 0.80 < dc.illumination_efficiency(2.0, 0.40) < 0.84
    # Surface error makes the same dish less efficient at 24 GHz than at 10 GHz.
    assert dc.net_efficiency(0.6, 24.192, 0.5) < dc.net_efficiency(0.6, 10.368, 0.5)


def test_blockage_smaller_at_24ghz():
    d = 0.75
    b10 = dc.blockage_efficiency(3 * dc.wavelength_m(10.368), d)
    b24 = dc.blockage_efficiency(3 * dc.wavelength_m(24.192), d)
    assert 0.95 < b10 < b24 < 1.0
