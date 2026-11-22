"""Tests for the status line parser, using lines captured from the AV 20."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "av_status", ROOT / "custom_components" / "denonavr" / "av_status.py"
)
av_status = importlib.util.module_from_spec(_spec)
sys.modules["av_status"] = av_status
_spec.loader.exec_module(av_status)

from .test_dirac_slots import received_lines


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("SYSDA Dolby Atmos          ", ("input_format", "Dolby Atmos")),
        ("SYSDA PCM                  ", ("input_format", "PCM")),
        ("SYSDA Dolby Audio - DD+    ", ("input_format", "Dolby Audio - DD+")),
        ("SYSDA Unknown              ", ("input_format", "Unknown")),
        ("SYSMI Dolby Atmos", ("decoded_mode", "Dolby Atmos")),
        ("SYSMI Multi Ch In", ("decoded_mode", "Multi Ch In")),
        ("SYSMI Dolby Audio - Dolby Digital Plus",
         ("decoded_mode", "Dolby Audio - Dolby Digital Plus")),
        ("SSINFAISSIG 25", ("input_signal", "25")),
        ("SSINFAISSIG 02", ("input_signal", "02")),
        ("SSINFAISFSV 48K", ("sample_rate", 48.0)),
        ("SSINFAISFSV 441", ("sample_rate", 44.1)),
        ("SSINFAISFSV NON", ("sample_rate", None)),
        ("SSSMG MOV", ("smart_select_group", "Movie")),
        ("SSSMG MUS", ("smart_select_group", "Music")),
    ],
)
def test_captured_lines(line, expected):
    assert av_status.parse_line(line) == expected


@pytest.mark.parametrize(
    "line", ["SSTTR ON", "SSLEVFL 50", "SSSDEFL 0121", "PSDIRAC 1", "SYSTEM X", "MSSTEREO"]
)
def test_other_lines_ignored(line):
    assert av_status.parse_line(line) is None


def test_every_captured_status_line_parses():
    keys = set()
    for log in sorted((ROOT / "captures").glob("*.log")):
        for line in received_lines(log):
            if line.startswith(("SYSDA", "SYSMI", "SSINFAISSIG", "SSINFAISFSV", "SSSMG")):
                parsed = av_status.parse_line(line)
                assert parsed is not None, line
                keys.add(parsed[0])
    assert keys == set(av_status.KEYS)


def test_signal_names():
    assert av_status.signal_name("25") == "Dolby Atmos"
    assert av_status.signal_name("01") == "Analog"
    assert av_status.signal_name("04") == "Dolby Digital Plus"
    assert av_status.signal_name("99") == "Unknown (99)"
    assert av_status.signal_name(None) is None


def test_sample_rates():
    assert av_status.parse_sample_rate("96K") == 96.0
    assert av_status.parse_sample_rate("882") == 88.2
    assert av_status.parse_sample_rate("") is None
    assert av_status.parse_sample_rate("XYZ") is None


@pytest.mark.parametrize(
    ("dirac", "mode", "expected"),
    [
        ("Slot 1", "DOLBY ATMOS", True),
        ("Slot 2", "STEREO", True),
        ("Off", "DOLBY ATMOS", False),
        ("Slot 1", "DIRECT", False),
        ("Slot 1", "PURE DIRECT", False),
        ("Slot 1", None, True),
        (None, "STEREO", None),
    ],
)
def test_dirac_effective(dirac, mode, expected):
    assert av_status.dirac_effective(dirac, mode) is expected
