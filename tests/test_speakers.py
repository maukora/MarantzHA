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
        ("SSSDEFL 0121", "distance", "FL", 121),
        ("SSSDEFL 0260", "distance", "FL", 260),
        ("SSSDESW 0000", "distance", "SW", 0),
        ("SSSDESTP 01S", "distance_step", None, "01S"),
        ("SSSDE END", "distance_end", None, None),
    ],
)
def test_captured_lines(line, kind, channel, value):
    parsed = speakers.parse_line(line)
    assert (parsed.kind, parsed.channel, parsed.value) == (kind, channel, value)


@pytest.mark.parametrize(
    "line", ["SSLEV END", "SSTTLFL 50", "SSINFAISSIG 25", "PSSWL 46", "SSLEVFL X"]
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


@pytest.mark.parametrize(
    ("raw", "step", "metres", "ms"),
    [
        (260, "01M", 2.6, None),  # Dirac Off: cm
        (121, "01S", None, 12.1),  # Dirac filter: 0.1 ms
        (0, "01S", None, 0.0),
        (121, None, None, None),  # unit not known yet
        (None, "01S", None, None),
    ],
)
def test_units(raw, step, metres, ms):
    assert speakers.distance_m(raw, step) == metres
    assert speakers.delay_ms(raw, step) == ms


def test_relative_distances_match_dirac_print():
    # Delays from Markus's settings print (16 Nov 2026, slot 1).
    delays = {"FL": 12.3, "FR": 12.1, "C": 12.9, "SL": 13.3, "SR": 12.4, "FHR": 10.9, "SW": 0.0}
    rel = speakers.relative_distances(delays)
    assert "SW" not in rel
    assert rel["SL"] == 0.0
    assert rel["C"] == 0.14
    assert rel["SR"] == 0.31
    assert rel["FL"] == 0.34
    assert rel["FR"] == 0.41
    assert rel["FHR"] == 0.82
    assert speakers.relative_distances({"SW": 0.0}) == {}
