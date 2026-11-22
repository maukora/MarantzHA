"""Parse Dirac Live filter slot info pushed by Denon/Marantz receivers.

The receiver pushes a block like this over telnet (verified on a Marantz AV 20),
after input, sound mode or signal changes and after leaving the setup menu:

    OPDLSSL1NAME ALeft-HigherLowerShelfs      (name is right-padded with spaces)
    OPDLSSL1IMP ON
    OPDLSSL1TYP ART
    ...
    OPDLSSL3NAME                              (empty slot)
    OPDLSSL3IMP OFF
    OPDLSSL3TYP NSA
    OPDLS END

The denonavr library passes these to "OP" callbacks with the "OP" prefix removed.
This module has no Home Assistant imports so it can be unit tested on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SLOT_NUMBERS = (1, 2, 3)

# Values used by denonavr's DenonAVRDirac.dirac_filter / async_dirac_filter.
LIB_OFF = "Off"
LIB_SLOTS = {n: f"Slot {n}" for n in SLOT_NUMBERS}

OPTION_OFF = "Off"

_SLOT_LINE = re.compile(r"DLSSL([1-3])(NAME|IMP|TYP)(?: (.*))?")


@dataclass
class DiracSlot:
    """One Dirac Live filter slot."""

    number: int
    name: str = ""
    imported: bool | None = None
    filter_type: str | None = None

    @property
    def is_empty(self) -> bool:
        """Return True when the slot is known to hold no filter."""
        return self.imported is False


class DiracSlotTracker:
    """Keep the latest Dirac slot info from OPDLS telnet lines."""

    def __init__(self) -> None:
        """Initialize with unknown slots."""
        self.slots: dict[int, DiracSlot] = {n: DiracSlot(n) for n in SLOT_NUMBERS}

    def handle_op_parameter(self, parameter: str) -> bool:
        """Process the parameter of an "OP" telnet event.

        Returns True when the end of an OPDLS block was seen, which is the
        moment to write state.
        """
        line = parameter.rstrip()
        if not line.startswith("DLS"):
            return False
        if line == "DLS END":
            return True
        match = _SLOT_LINE.fullmatch(line)
        if match is None:
            return False
        slot = self.slots[int(match.group(1))]
        field, value = match.group(2), (match.group(3) or "").strip()
        if field == "NAME":
            slot.name = value
        elif field == "IMP":
            slot.imported = {"ON": True, "OFF": False}.get(value)
        else:
            slot.filter_type = value or None
        return False

    def handle_line(self, line: str) -> bool:
        """Process a full telnet line (with "OP" prefix). For tests and tools."""
        if not line.startswith("OP"):
            return False
        return self.handle_op_parameter(line[2:])

    def labels(self) -> dict[int, str]:
        """Return a unique display label per slot.

        The filter name from Dirac Live when known, otherwise "Slot n". If two
        slots share a name, the slot number is added so labels stay unique.
        """
        names = [s.name for s in self.slots.values() if s.name]
        labels: dict[int, str] = {}
        for n, slot in self.slots.items():
            if not slot.name:
                labels[n] = f"Slot {n}"
            elif names.count(slot.name) > 1:
                labels[n] = f"Slot {n}: {slot.name}"
            else:
                labels[n] = slot.name
        return labels

    def options(self, active: str | None = None) -> list[str]:
        """Return select options: "Off" plus every slot that isn't empty.

        An empty slot is still listed if it is the active one (``active`` is
        the library value, e.g. "Slot 3").
        """
        labels = self.labels()
        options = [OPTION_OFF]
        for n, slot in self.slots.items():
            if not slot.is_empty or active == LIB_SLOTS[n]:
                options.append(labels[n])
        return options

    def option_for(self, lib_value: str | None) -> str | None:
        """Map a library value ("Off", "Slot 1", ...) to a select option."""
        if lib_value is None:
            return None
        if lib_value == LIB_OFF:
            return OPTION_OFF
        for n, value in LIB_SLOTS.items():
            if value == lib_value:
                return self.labels()[n]
        return None

    def lib_value_for(self, option: str) -> str | None:
        """Map a select option back to the library value."""
        if option == OPTION_OFF:
            return LIB_OFF
        for n, label in self.labels().items():
            if label == option:
                return LIB_SLOTS[n]
        return None

    def as_attributes(self) -> dict[str, str | bool | None]:
        """Return slot details as state attributes."""
        attrs: dict[str, str | bool | None] = {}
        for n, slot in self.slots.items():
            attrs[f"slot_{n}_name"] = slot.name or None
            attrs[f"slot_{n}_imported"] = slot.imported
            attrs[f"slot_{n}_filter_type"] = slot.filter_type
        return attrs

    def restore_from_attributes(self, attrs: dict) -> None:
        """Restore slot details saved by as_attributes (after an HA restart)."""
        for n, slot in self.slots.items():
            name = attrs.get(f"slot_{n}_name")
            imported = attrs.get(f"slot_{n}_imported")
            filter_type = attrs.get(f"slot_{n}_filter_type")
            slot.name = name if isinstance(name, str) else ""
            slot.imported = imported if isinstance(imported, bool) else None
            slot.filter_type = filter_type if isinstance(filter_type, str) else None
