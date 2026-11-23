"""Speaker layout (e.g. "7.1.4") and per-speaker info for dashboards.

Which speakers are set up comes from the receiver's own SSSDE dump (it only
lists configured speakers). Positions are the usual Dolby/ITU angles for each
channel, not measured ones: azimuth in degrees (0 = front, negative = left),
elevation in degrees (0 = ear height). x/y put them on a unit circle around
the listener (x right, y front), handy for a picture-elements card.

OPINFASP has one digit per output (0 none, 1 idle, 2 playing). The order
below matches the AV 20 captures for the first 8 positions and for the front
and rear heights (positions 9-10 and 15-16); the rest follows the same Denon
order but is not verified.

No Home Assistant imports.
"""

from __future__ import annotations

import math

from .speakers import channel_name, is_subwoofer

# channel -> (group, azimuth, elevation)
POSITIONS: dict[str, tuple[str, int, int]] = {
    "FL": ("front", -30, 0),
    "FR": ("front", 30, 0),
    "C": ("center", 0, 0),
    "FWL": ("wide", -60, 0),
    "FWR": ("wide", 60, 0),
    "SL": ("surround", -100, 0),
    "SR": ("surround", 100, 0),
    "SBL": ("surround_back", -145, 0),
    "SBR": ("surround_back", 145, 0),
    "SB": ("surround_back", 180, 0),
    "FHL": ("height", -40, 40),
    "FHR": ("height", 40, 40),
    "TFL": ("height", -45, 60),
    "TFR": ("height", 45, 60),
    "TML": ("height", -90, 80),
    "TMR": ("height", 90, 80),
    "TRL": ("height", -135, 60),
    "TRR": ("height", 135, 60),
    "RHL": ("height", -140, 40),
    "RHR": ("height", 140, 40),
    "FDL": ("height", -30, 30),
    "FDR": ("height", 30, 30),
    "SDL": ("height", -100, 30),
    "SDR": ("height", 100, 30),
    "BDL": ("height", -145, 30),
    "BDR": ("height", 145, 30),
    "SHL": ("height", -100, 40),
    "SHR": ("height", 100, 40),
    "TS": ("height", 0, 90),
    "CH": ("height", 0, 40),
    "SW": ("subwoofer", -20, 0),
    "SW2": ("subwoofer", 20, 0),
    "SW3": ("subwoofer", -160, 0),
    "SW4": ("subwoofer", 160, 0),
}

ASP_ORDER = (
    "FL", "FR", "C", "SW", "SL", "SR", "SBL", "SBR", "SB",
    "FHL", "FHR", "TFL", "TFR", "TML", "TMR", "RHL", "RHR", "TRL", "TRR",
    "FWL", "FWR", "FDL", "FDR", "SDL", "SDR", "BDL", "BDR", "SHL", "SHR", "TS", "CH",
)  # fmt: skip

# Display order: front to back, then heights, then subs.
_ORDER = {code: i for i, code in enumerate(POSITIONS)}


def layout_name(channels: set[str] | list[str]) -> str | None:
    """'7.1.4' style name: ear-level speakers . subwoofers . heights."""
    if not channels:
        return None
    subs = sum(1 for ch in channels if is_subwoofer(ch))
    heights = sum(1 for ch in channels if POSITIONS.get(ch, ("",))[0] == "height")
    bed = len(set(channels)) - subs - heights
    return f"{bed}.{subs}.{heights}" if heights else f"{bed}.{subs}"


def playing_channels(pattern: str | None) -> set[str] | None:
    """Channels marked 2 in OPINFASP (all subwoofers share the SW digit)."""
    if not pattern:
        return None
    playing = {ASP_ORDER[i] for i, c in enumerate(pattern[: len(ASP_ORDER)]) if c == "2"}
    if "SW" in playing:
        playing |= {"SW2", "SW3", "SW4"}
    return playing


def speaker_list(
    channels: set[str] | list[str],
    levels: dict[str, float],
    delays: dict[str, float],
    relative: dict[str, float],
    distances: dict[str, float],
    pattern: str | None,
) -> list[dict]:
    """One dict per configured speaker, in display order."""
    playing = playing_channels(pattern)
    result = []
    for ch in sorted(channels, key=lambda c: _ORDER.get(c, 99)):
        group, azimuth, elevation = POSITIONS.get(ch, ("other", 0, 0))
        rad = math.radians(azimuth)
        item = {
            "channel": ch,
            "name": channel_name(ch),
            "group": group,
            "azimuth": azimuth,
            "elevation": elevation,
            "x": round(math.sin(rad), 2),
            "y": round(math.cos(rad), 2),
            "playing": None if playing is None else ch in playing,
            "level_db": levels.get(ch),
        }
        if ch in delays:
            item["delay_ms"] = delays[ch]
        if ch in relative:
            item["relative_distance_m"] = relative[ch]
        if ch in distances:
            item["distance_m"] = distances[ch]
        result.append(item)
    return result
