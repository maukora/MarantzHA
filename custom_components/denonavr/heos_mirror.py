"""Show what HEOS is playing (art, title, artist) on the receiver's player.

HEOS-era receivers stream network audio through HEOS, and the receiver's own
API doesn't report track info or cover art for it. The core HEOS integration
does, on a separate media player. This finds that player (same serial number
as the receiver) and reads its state. It talks to nothing itself, so there is
no extra connection to the receiver.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.media_player import MediaPlayerState
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

HEOS_DOMAIN = "heos"
# Inputs the receiver shows while HEOS is the source.
HEOS_SOURCES = {"HEOS Music", "HEOS", "NET", "Online Music", "NETWORK"}
MIRRORED_STATES = {MediaPlayerState.PLAYING, MediaPlayerState.PAUSED}


def serial_from_entry(serial: str | None, unique_id: str | None) -> str | None:
    """Receiver serial: from config data, else the end of the unique id."""
    if serial:
        return serial
    if unique_id and "-" in unique_id:
        return unique_id.rsplit("-", 1)[1] or None
    return None


def find_heos_entity(hass: HomeAssistant, serial: str | None, name: str | None) -> str | None:
    """Entity id of the HEOS player for this receiver, or None.

    Matched by serial number; if HEOS has no serial for it, by device name
    when exactly one HEOS device has that name.
    """
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    by_name = []
    for entry in ent_reg.entities.values():
        if entry.platform != HEOS_DOMAIN or entry.domain != "media_player":
            continue
        if entry.disabled_by is not None or entry.device_id is None:
            continue
        if (device := dev_reg.async_get(entry.device_id)) is None:
            continue
        if serial and device.serial_number == serial:
            return entry.entity_id
        if name and (device.name_by_user or device.name or "").strip() == name.strip():
            by_name.append(entry.entity_id)
    return by_name[0] if len(by_name) == 1 else None


def mirror_state(heos: State | None, source: str | None, power_on: bool) -> State | None:
    """The HEOS state to mirror right now, or None."""
    if heos is None or not power_on or source not in HEOS_SOURCES:
        return None
    if heos.state not in MIRRORED_STATES:
        return None
    return heos


def image_url(heos: State) -> str | None:
    """Cover art URL that Home Assistant can fetch and proxy."""
    picture = heos.attributes.get("entity_picture")
    if isinstance(picture, str) and picture.startswith(("http://", "https://")):
        return picture
    return None


def attr(heos: State, name: str) -> Any:
    """One attribute of the HEOS state."""
    return heos.attributes.get(name)


def position_updated_at(heos: State) -> datetime | None:
    """media_position_updated_at as a datetime."""
    value = heos.attributes.get("media_position_updated_at")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None
