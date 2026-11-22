"""Tests for the speaker level/distance parser, using AV 20 captures."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "speakers", ROOT / "custom_components" / "denonavr" / "speakers.py"
)
speakers = importlib.util.module_from_spec(_spec)
sys.modules["speakers"] = speakers
_spec.loader.exec_module(speakers)

from .test_dirac_slots import received_lines

FIRST = ROOT / "captures" / "20261122-2227-first-probe.log"


@pytest.mark.parametrize(
    ("line", "kind", "channel", "value"),
    [
        ("SSLEVFL 50", "level", "FL", 0.0),
        ("SSLEVFL 52", "level", "FL", 2.0),
        ("SSLEVFR 535", "level", "FR", 3.5),
        ("SSLEVSL 495", "level", "SL", -0.5),
        ("SSLEVSW 46", "level", "SW", -4.0),
        ("SSLEVSW2 485", "level", "SW2", -1.5),
        ("SSSDEFL 0121", "distance", "FL", 1.21),
        ("SSSDEFL 0260", "distance", "FL", 2.6),
        ("SSSDESW 0000", "distance", "SW", 0.0),
        ("SSSDESTP 01S", "distance_step", None, "01S"),
    ],
)
def test_captured_lines(line, kind, channel, value):
    parsed = speakers.parse_line(line)
    assert (parsed.kind, parsed.channel, parsed.value) == (kind, channel, value)


@pytest.mark.parametrize(
    "line", ["SSLEV END", "SSSDE END", "SSTTLFL 50", "SSINFAISSIG 25", "PSSWL 46", "SSLEVFL X"]
)
def test_other_lines_ignored(line):
    assert speakers.parse_line(line) is None


def test_capture_speakers():
    distances, levels = {}, {}
    for line in received_lines(FIRST):
        if (p := speakers.parse_line(line)) is None:
            continue
        if p.kind == "distance":
            distances[p.channel] = p.value
        elif p.kind == "level":
            levels[p.channel] = p.value
    # Distances only for the configured speakers (Markus's 9.4.4-ish layout).
    assert set(distances) == {
        "FL", "FR", "C", "SW", "SW2", "SW3", "SW4", "SL", "SR", "SBL", "SBR",
        "FHL", "FHR", "RHL", "RHR",
    }
    # Levels for every possible channel; all have a readable name.
    assert len(levels) > len(distances)
    assert all(speakers.channel_name(ch) != ch for ch in levels)
