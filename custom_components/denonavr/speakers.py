"""Parse per-speaker channel levels and distances pushed by the receiver.

Verified on a Marantz AV 20: after every Dirac slot change the receiver pushes
a full dump (Dirac stores levels and distances per filter):

    SSLEVFL 52        level: 2 digits = whole dB, 3 digits = tenths; 50 = 0 dB
    SSLEVFR 535       -> +3.5 dB
    ...
    SSLEV END
    SSSDEFL 0121      distance/delay for configured speakers only, then
    SSSDESTP 01S      the unit of those values:
                        01M (Dirac Off): distance in cm   -> 1.21 m
                        01S (Dirac filter): delay in 0.1 ms -> 12.1 ms
                      (matches the delays in the receiver's settings print:
                       subwoofer 0 ms, other channels 11-13 ms)

Levels are sent for every possible channel, distances only for the speakers
that are set up, so the distance lines decide which speakers get entities.
No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass

LEVEL = "level"
DISTANCE = "distance"
DELAY = "delay"
DISTANCE_STEP = "distance_step"

CHANNEL_NAMES = {
    "FL": "Front left",
    "FR": "Front right",
    "C": "Center",
    "SW": "Subwoofer",
    "SW2": "Subwoofer 2",
    "SW3": "Subwoofer 3",
    "SW4": "Subwoofer 4",
    "SL": "Surround left",
    "SR": "Surround right",
    "SB": "Surround back",
    "SBL": "Surround back left",
    "SBR": "Surround back right",
    "FHL": "Front height left",
    "FHR": "Front height right",
    "FWL": "Front wide left",
    "FWR": "Front wide right",
    "TFL": "Top front left",
    "TFR": "Top front right",
    "TML": "Top middle left",
    "TMR": "Top middle right",
    "TRL": "Top rear left",
    "TRR": "Top rear right",
    "RHL": "Rear height left",
    "RHR": "Rear height right",
    "FDL": "Front Dolby left",
    "FDR": "Front Dolby right",
    "SDL": "Surround Dolby left",
    "SDR": "Surround Dolby right",
    "BDL": "Back Dolby left",
    "BDR": "Back Dolby right",
    "SHL": "Surround height left",
    "SHR": "Surround height right",
    "TS": "Top surround",
    "CH": "Center height",
}


@dataclass(frozen=True)
class SpeakerValue:
    """One parsed speaker line."""

    kind: str  # LEVEL, DISTANCE or DISTANCE_STEP
    channel: str | None
    value: float | str | None


def channel_name(code: str) -> str:
    """Return a readable channel name (falls back to the code)."""
    return CHANNEL_NAMES.get(code, code)


def parse_level(value: str) -> float | None:
    """Convert a level code to dB relative to 0: "50" -> 0.0, "535" -> 3.5."""
    if not value.isdigit():
        return None
    if len(value) == 2:
        return float(int(value) - 50)
    if len(value) == 3:
        return round(int(value) / 10 - 50, 1)
    return None


SPEED_OF_SOUND_M_PER_MS = 0.343


def parse_distance(value: str) -> int | None:
    """Return the raw distance/delay number: "0121" -> 121."""
    if not value.isdigit():
        return None
    return int(value)


def is_delay_step(step: str | None) -> bool | None:
    """True if SSSDESTP says the values are delays, False for distances."""
    if not step:
        return None
    unit = step.strip()[-1:].upper()
    if unit == "S":
        return True
    if unit == "M":
        return False
    return None


def distance_m(raw: int | None, step: str | None) -> float | None:
    """Distance in metres, or None when the values are delays (or unknown)."""
    if raw is None or is_delay_step(step) is not False:
        return None
    return raw / 100


def delay_ms(raw: int | None, step: str | None) -> float | None:
    """Delay in ms, or None when the values are distances (or unknown)."""
    if raw is None or is_delay_step(step) is not True:
        return None
    return raw / 10


def is_subwoofer(channel: str) -> bool:
    """Return True for SW, SW2..SW4."""
    return channel.startswith("SW")


def relative_distances(delays: dict[str, float]) -> dict[str, float]:
    """Extra acoustic distance (m) of each speaker vs the closest one.

    A larger delay means the speaker is acoustically closer. Subwoofers are
    left out: their delay is dominated by processing latency.
    """
    speakers = {ch: d for ch, d in delays.items() if not is_subwoofer(ch)}
    if not speakers:
        return {}
    closest = max(speakers.values())
    return {
        ch: round((closest - d) * SPEED_OF_SOUND_M_PER_MS, 2) for ch, d in speakers.items()
    }


def parse_speaker(event: str, parameter: str) -> SpeakerValue | None:
    """Parse an "SS" telnet event into a SpeakerValue, or None."""
    if event != "SS":
        return None
    param = parameter.strip()
    if param.startswith("LEV") and param != "LEV END":
        channel, _, value = param[3:].partition(" ")
        if channel and (level := parse_level(value)) is not None:
            return SpeakerValue(LEVEL, channel, level)
        return None
    if param.startswith("SDESTP "):
        return SpeakerValue(DISTANCE_STEP, None, param[7:])
    if param.startswith("SDE") and param != "SDE END":
        channel, _, value = param[3:].partition(" ")
        if channel and (distance := parse_distance(value)) is not None:
            return SpeakerValue(DISTANCE, channel, distance)
    return None


def parse_line(line: str) -> SpeakerValue | None:
    """Parse a full telnet line. For tests and tools."""
    return parse_speaker(line[:2], line[2:])
