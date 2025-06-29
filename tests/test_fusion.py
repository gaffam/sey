import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gambusia.fusion import fuse_pesticide_signals


def test_high_voc_nh3():
    score, reasons = fuse_pesticide_signals({"voc": 500, "nh3": 70})
    assert score == 0.6
    assert "voc_and_nh3_high" in reasons


def test_orp_ph_contribution():
    score, reasons = fuse_pesticide_signals({"orp": 750, "ph": 8.0})
    assert score > 0
    assert "orp_high" in reasons
    assert "ph_out_of_range" in reasons
