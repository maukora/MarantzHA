"""Tests for the audio settings parser, using AV 20 captures."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "custom_components" / "denonavr"

# Load the two pure modules as a tiny package without importing the
# integration's __init__ (which needs Home Assistant).
_pkg = types.ModuleType("denonavr_pure")
_pkg.__path__ = [str(PKG_DIR)]
sys.modules["denonavr_pure"] = _pkg
for _name in ("speakers", "audio_settings"):
    _spec = importlib.util.spec_from_file_location(f"denonavr_pure.{_name}", PKG_DIR / f"{_name}.py")
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[f"denonavr_pure.{_name}"] = _mod
    _spec.loader.exec_module(_mod)
audio = sys.modules["denonavr_pure.audio_settings"]

from .test_dirac_slots import received_lines

CAPTURES = sorted((ROOT / "captures").glob("20261122-*.log"))


@pytest.mark.parametrize(
    ("line", "key", "value"),
    [
        ("PSSWL 46", "subwoofer_level", -4.0),
        ("PSSWL 465", "subwoofer_level", -3.5),
        ("PSLFE 00", "lfe_level", 0),
        ("PSLFE 10", "lfe_level", -10),
        ("PSBAS 50", "bass", 0),
        ("PSTRE 56", "treble", 6),
        ("PSTONE CTRL OFF", "tone_control", False),
        ("PSTONE CTRL ON", "tone_control", True),
        ("PSDRC OFF", "drc", "Off"),
        ("PSDRC HI", "drc", "High"),
        ("CVFL 50", "channel_volume", ("FL", 0.0)),
        ("CVSR 535", "channel_volume", ("SR", 3.5)),
        ("OPALSSET ON", "auto_lip_sync", True),
        ("OPALSVAL 000", "auto_lip_sync_value", 0),
        ("OPINFASP 22121111011000011000000000000000", "active_speakers",
         "22121111011000011000000000000000"),
        ("OPINFINS 22222222111111000000", "input_channels", "22222222111111000000"),
    ],
)
def test_captured_lines(line, key, value):
    assert audio.parse_line(line) == (key, value)


@pytest.mark.parametrize(
    "line",
    ["PSSWL ON", "PSSWL2 50", "CVEND", "CVTTR ON", "CVTTR 50", "PSLFC OFF", "OPALSDSP ON",
     "PSDRC X", "PSDELAY 162", "SSLEVFL 50"],
)
def test_other_lines_ignored(line):
    assert audio.parse_line(line) is None


@pytest.mark.parametrize(("db", "code"), [(0, "50"), (3.5, "535"), (-3.5, "465"), (-4, "46"),
                                          (12, "62"), (-12, "38"), (0.5, "505")])
def test_encode_level_round_trips(db, code):
    assert audio.encode_level(db) == code
    assert audio.parse_line(f"PSSWL {code}") == ("subwoofer_level", float(db))


def test_counts():
    # Dolby Digital Plus 2.0 on Markus's 7.1.4: FL, FR and the sub play.
    pattern = "22121111011000011000000000000000"
    assert audio.count_playing(pattern) == 3
    assert audio.count_set_up(pattern) == 12
    assert audio.count_playing("22222222022000022000000000000000") == 12  # Atmos


def test_every_capture_line_of_these_kinds_parses():
    seen = set()
    for path in CAPTURES:
        for line in received_lines(path):
            if (parsed := audio.parse_line(line)) is not None:
                seen.add(parsed[0])
    assert {"subwoofer_level", "lfe_level", "bass", "tone_control", "drc",
            "channel_volume", "auto_lip_sync", "auto_lip_sync_value",
            "active_speakers", "input_channels"} <= seen
