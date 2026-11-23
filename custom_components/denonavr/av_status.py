"""Parse signal/status lines pushed by Denon/Marantz receivers over telnet.

Formats verified on a Marantz AV 20 (captures/20261122-*.log). The denonavr
library splits each line into an event (first 2 characters) and a parameter;
these helpers take that pair. No Home Assistant imports, so they can be unit
tested on their own.
"""

from __future__ import annotations

# Telnet lines (verified)          -> key, value
#   SYSDA Dolby Atmos   (padded)   -> input_format, "Dolby Atmos"
#   SYSMI Multi Ch In              -> decoded_mode, "Multi Ch In"
#   SSINFAISSIG 25                 -> input_signal, "25"  (code, see SIGNAL_CODES)
#   SSINFAISFSV 48K / 441 / NON    -> sample_rate, 48.0 / 44.1 / None   (kHz)
#   SSSMG MOV                      -> smart_select_group, "Movie"
INPUT_FORMAT = "input_format"
DECODED_MODE = "decoded_mode"
INPUT_SIGNAL = "input_signal"
SAMPLE_RATE = "sample_rate"
SMART_SELECT_GROUP = "smart_select_group"

KEYS = (INPUT_FORMAT, DECODED_MODE, INPUT_SIGNAL, SAMPLE_RATE, SMART_SELECT_GROUP)

# Signal codes seen in the captures. Add more as they show up.
SIGNAL_CODES = {
    "01": "Analog",  # seen in HA with SYSDA "Analog"
    "02": "PCM",
    "04": "Dolby Digital Plus",
    "12": "No signal",
    "25": "Dolby Atmos",
}

SMART_SELECT_GROUPS = {"MOV": "Movie", "MUS": "Music", "GAM": "Game"}

# Read-only queries with a verified reply, sent once after setup so the
# sensors have a value before the next change is pushed.
INITIAL_QUERIES = ("SSINFAISSIG ?", "SSINFAISFSV ?")

# Sound modes where Dirac applies only distances and levels, no filter.
DIRECT_SOUND_MODES = {"DIRECT", "PURE DIRECT", "PURE_DIRECT"}


def parse_sample_rate(value: str) -> float | None:
    """Convert the receiver's sample rate code to kHz.

    "48K" -> 48.0, "441" -> 44.1 (three/four digits are tenths of kHz),
    "NON" -> None (no signal).
    """
    value = value.strip().upper()
    if not value or value == "NON":
        return None
    if value.endswith("K"):
        try:
            return float(value[:-1])
        except ValueError:
            return None
    if value.isdigit():
        return int(value) / 10
    return None


def signal_name(code: str | None) -> str | None:
    """Return a readable name for a SSINFAISSIG code."""
    if code is None:
        return None
    return SIGNAL_CODES.get(code, f"Unknown ({code})")


def parse_status(event: str, parameter: str) -> tuple[str, str | float | None] | None:
    """Return (key, value) for a status line, or None if it isn't one."""
    param = parameter.rstrip()
    if event == "SY":
        if param.startswith("SDA "):
            return INPUT_FORMAT, param[4:].strip() or None
        if param.startswith("SMI "):
            return DECODED_MODE, param[4:].strip() or None
        return None
    if event == "SS":
        if param.startswith("INFAISSIG "):
            return INPUT_SIGNAL, param[10:].strip() or None
        if param.startswith("INFAISFSV "):
            return SAMPLE_RATE, parse_sample_rate(param[10:])
        if param.startswith("SMG "):
            group = param[4:].strip()
            return SMART_SELECT_GROUP, SMART_SELECT_GROUPS.get(group, group or None)
    return None


def parse_line(line: str) -> tuple[str, str | float | None] | None:
    """Parse a full telnet line. For tests and tools."""
    return parse_status(line[:2], line[2:])


def dirac_effective(dirac_filter: str | None, sound_mode_raw: str | None) -> bool | None:
    """Return whether a Dirac Live filter is actually applied.

    None when the slot is unknown. False when Dirac is off or the sound mode
    is Direct/Pure Direct (only distances and levels apply there).
    """
    if dirac_filter is None:
        return None
    if dirac_filter == "Off":
        return False
    return sound_mode_raw is None or sound_mode_raw.strip().upper() not in DIRECT_SOUND_MODES
