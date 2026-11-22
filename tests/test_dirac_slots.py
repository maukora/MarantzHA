"""Tests for the Dirac slot parser, using lines captured from the AV 20."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPTURE = ROOT / "captures" / "20261122-2230-snd-probe.log"

# Load the module directly so the tests don't need Home Assistant installed.
_spec = importlib.util.spec_from_file_location(
    "dirac_slots", ROOT / "custom_components" / "denonavr" / "dirac_slots.py"
)
dirac_slots = importlib.util.module_from_spec(_spec)
sys.modules["dirac_slots"] = dirac_slots
_spec.loader.exec_module(dirac_slots)
DiracSlotTracker = dirac_slots.DiracSlotTracker

# Verbatim from the capture, including the right padding on names.
BLOCK = [
    "OPDLSSL1NAME ALeft-HigherLowerShelfs                                     ",
    "OPDLSSL1IMP ON",
    "OPDLSSL1TYP ART",
    "OPDLSSL2NAME ArendalLeft                                                 ",
    "OPDLSSL2IMP ON",
    "OPDLSSL2TYP ART",
    "OPDLSSL3NAME                                                             ",
    "OPDLSSL3IMP OFF",
    "OPDLSSL3TYP NSA",
    "OPDLS END",
]


def received_lines(path: Path) -> list[str]:
    """Return the receiver lines ("<<") from a probe log, padding kept."""
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*[\d.]+ << (.*)$", raw)
        if m:
            lines.append(m.group(1))
    return lines


def fed(lines: list[str]) -> tuple[DiracSlotTracker, int]:
    tracker = DiracSlotTracker()
    ends = sum(tracker.handle_line(line) for line in lines)
    return tracker, ends


def test_block_parsed():
    tracker, ends = fed(BLOCK)
    assert ends == 1
    s = tracker.slots
    assert (s[1].name, s[1].imported, s[1].filter_type) == (
        "ALeft-HigherLowerShelfs", True, "ART")
    assert (s[2].name, s[2].imported, s[2].filter_type) == ("ArendalLeft", True, "ART")
    assert (s[3].name, s[3].imported, s[3].filter_type) == ("", False, "NSA")
    assert s[3].is_empty


def test_only_end_line_returns_true():
    tracker = DiracSlotTracker()
    assert [tracker.handle_line(line) for line in BLOCK] == [False] * 9 + [True]


def test_other_op_lines_ignored():
    tracker = DiracSlotTracker()
    for line in ["OPINFASP 2222", "OPSMLALL MOV021Dolby Atmos", "OPSMLALL END", "PSDIRAC 1"]:
        assert tracker.handle_line(line) is False
    assert all(s.name == "" and s.imported is None for s in tracker.slots.values())


def test_capture_file():
    lines = received_lines(CAPTURE)
    tracker, ends = fed(lines)
    assert ends == 9  # the block was pushed 9 times during the probe
    assert tracker.slots[1].name == "ALeft-HigherLowerShelfs"
    assert tracker.slots[2].name == "ArendalLeft"
    assert tracker.slots[3].is_empty


def test_options_hide_empty_slot():
    tracker, _ = fed(BLOCK)
    assert tracker.options("Slot 1") == ["Off", "ALeft-HigherLowerShelfs", "ArendalLeft"]
    # An empty slot stays listed if it's the active one, so the state is valid.
    assert tracker.options("Slot 3") == [
        "Off", "ALeft-HigherLowerShelfs", "ArendalLeft", "Slot 3"]


def test_options_before_names_known():
    tracker = DiracSlotTracker()
    assert tracker.options(None) == ["Off", "Slot 1", "Slot 2", "Slot 3"]
    assert tracker.option_for("Slot 2") == "Slot 2"


def test_option_mapping_round_trip():
    tracker, _ = fed(BLOCK)
    for lib in ["Off", "Slot 1", "Slot 2", "Slot 3"]:
        assert tracker.lib_value_for(tracker.option_for(lib)) == lib
    assert tracker.option_for("Slot 2") == "ArendalLeft"
    assert tracker.option_for(None) is None
    assert tracker.lib_value_for("nope") is None


def test_duplicate_names_get_slot_prefix():
    tracker, _ = fed(BLOCK + ["OPDLSSL3NAME ArendalLeft   ", "OPDLSSL3IMP ON", "OPDLS END"])
    labels = tracker.labels()
    assert labels[2] == "Slot 2: ArendalLeft"
    assert labels[3] == "Slot 3: ArendalLeft"
    assert labels[1] == "ALeft-HigherLowerShelfs"


def test_attributes_restore():
    tracker, _ = fed(BLOCK)
    attrs = tracker.as_attributes()
    assert attrs["slot_1_name"] == "ALeft-HigherLowerShelfs"
    assert attrs["slot_3_name"] is None
    restored = DiracSlotTracker()
    restored.restore_from_attributes(attrs)
    assert restored.labels() == tracker.labels()
    assert restored.options("Slot 1") == tracker.options("Slot 1")


def test_capture_psdirac_values_map():
    # Every PSDIRAC value seen in the captures maps to a library value we handle.
    values = {line.split(" ", 1)[1] for p in sorted((ROOT / "captures").glob("*.log"))
              for line in received_lines(p) if line.startswith("PSDIRAC ")}
    assert values == {"1", "2", "OFF"}
