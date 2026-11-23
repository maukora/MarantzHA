"""Parse and build telnet lines for audio settings (sub/LFE/tone/DRC, trims, lip sync).

Lines seen on a Marantz AV 20 (captures/20261122-*.log):

    PSSWL 46            subwoofer level: like channel levels, 50 = 0 dB,
                        3 digits = half dB (465 = -3.5 dB). Range -12..+12.
    PSLFE 00            LFE level 0..-10 dB (sent as 00..10)
    PSBAS 50 / PSTRE 50 bass/treble, 50 = 0 dB, range 44..56 (-6..+6 dB)
    PSTONE CTRL OFF     tone control on/off (bass/treble only apply when on)
    PSDRC OFF           dynamic range compression: AUTO/LOW/MID/HI/OFF
    CVFL 50 ... CVEND   channel volume trims for the channels in use, 50 = 0 dB
    OPALSSET ON         auto lip sync on/off
    OPALSVAL 000        auto lip sync value (ms)
    OPINFASP 2212...    one digit per output speaker: 0 = not set up,
                        1 = set up but silent, 2 = playing
    OPINFINS 2222...    one digit per input channel: 2 = present in the signal

No Home Assistant imports.
"""

from __future__ import annotations

from .speakers import CHANNEL_NAMES, parse_level

SUBWOOFER_LEVEL = "subwoofer_level"
LFE_LEVEL = "lfe_level"
BASS = "bass"
TREBLE = "treble"
TONE_CONTROL = "tone_control"
DRC = "drc"
CHANNEL_VOLUME = "channel_volume"
AUTO_LIP_SYNC = "auto_lip_sync"
AUTO_LIP_SYNC_VALUE = "auto_lip_sync_value"
ACTIVE_SPEAKERS = "active_speakers"
INPUT_CHANNELS = "input_channels"

DRC_OPTIONS = {"AUTO": "Auto", "LOW": "Low", "MID": "Medium", "HI": "High", "OFF": "Off"}
DRC_CODES = {name: code for code, name in DRC_OPTIONS.items()}

# Read-only queries for the current values (the library sends the same ones
# at connect, possibly before our entities listen).
SETTINGS_QUERIES = (
    "PSSWL ?",
    "PSLFE ?",
    "PSBAS ?",
    "PSTRE ?",
    "PSTONE CTRL ?",
    "PSDRC ?",
    "CV?",
)

# Channels in CV lines that aren't speakers (tactile transducer etc.).
NOT_CHANNELS = {"TTR", "END"}


def encode_level(db: float) -> str:
    """0.0 -> "50", 3.5 -> "535", -3.5 -> "465", -4 -> "46" (half-dB steps)."""
    value = 50 + round(db * 2) / 2
    if value == int(value):
        return f"{int(value):02d}"
    return f"{int(value):02d}5"


def tone_code(db: int) -> str:
    """Bass/treble dB (-6..+6) -> "44".."56"."""
    return f"{50 + int(db):02d}"


def parse_setting(event: str, parameter: str) -> tuple[str, object] | None:
    """Parse one telnet event into (key, value), or None."""
    param = parameter.strip()
    if event == "PS":
        name, _, value = param.partition(" ")
        if name == "SWL" and (level := parse_level(value)) is not None:
            return SUBWOOFER_LEVEL, level
        if name == "LFE" and value.isdigit():
            return LFE_LEVEL, -int(value)
        if name in ("BAS", "TRE") and value.isdigit():
            return (BASS if name == "BAS" else TREBLE), int(value) - 50
        if param in ("TONE CTRL ON", "TONE CTRL OFF"):
            return TONE_CONTROL, param.endswith("ON")
        if name == "DRC" and value in DRC_OPTIONS:
            return DRC, DRC_OPTIONS[value]
        return None
    if event == "CV":
        channel, _, value = param.partition(" ")
        if channel in NOT_CHANNELS or channel not in CHANNEL_NAMES:
            return None
        if (level := parse_level(value)) is not None:
            return CHANNEL_VOLUME, (channel, level)
        return None
    if event == "OP":
        if param in ("ALSSET ON", "ALSSET OFF"):
            return AUTO_LIP_SYNC, param.endswith("ON")
        if param.startswith("ALSVAL ") and param[7:].isdigit():
            return AUTO_LIP_SYNC_VALUE, int(param[7:])
        if param.startswith("INFASP ") and param[7:].isdigit():
            return ACTIVE_SPEAKERS, param[7:]
        if param.startswith("INFINS ") and param[7:].isdigit():
            return INPUT_CHANNELS, param[7:]
    return None


def parse_line(line: str) -> tuple[str, object] | None:
    """Parse a full telnet line. For tests and tools."""
    return parse_setting(line[:2], line[2:])


def count_playing(pattern: str) -> int:
    """Number of channels marked 2 (playing / present in the signal)."""
    return pattern.count("2")


def count_set_up(pattern: str) -> int:
    """Number of channels that exist (marked 1 or 2)."""
    return sum(1 for c in pattern if c != "0")
