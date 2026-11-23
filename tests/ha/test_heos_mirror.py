"""HEOS track info and art shown on the receiver's media player."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.denonavr import heos_mirror
from custom_components.denonavr.media_player import DenonDevice

from .test_select import make_entry

HEOS_ID = "media_player.marantz_av_20"
ART = "http://resources.wimpmusic.com/images/1b6359f5/640x640.jpg"
PLAYING = {
    "media_title": "Paint It, Black",
    "media_artist": "Ciara",
    "media_album_name": "Paint It, Black",
    "media_duration": 215,
    "media_position": 42,
    "media_position_updated_at": datetime(2026, 11, 23, 11, 0, tzinfo=UTC),
    "entity_picture": ART,
    "entity_picture_local": "/api/media_player_proxy/media_player.marantz_av_20?token=x",
}


def add_heos_player(hass: HomeAssistant, serial: str | None = "123456789", name="AV 20 ") -> str:
    heos_entry = MockConfigEntry(domain="heos", title="HEOS System")
    heos_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=heos_entry.entry_id,
        identifiers={("heos", "-1763064440")},
        manufacturer="Marantz",
        model="AV 20",
        name=name,
        serial_number=serial,
    )
    return er.async_get(hass).async_get_or_create(
        "media_player", "heos", "-1763064440", config_entry=heos_entry,
        device_id=device.id, suggested_object_id="marantz_av_20",
    ).entity_id


def test_serial_from_entry():
    assert heos_mirror.serial_from_entry("ABC", "x-y") == "ABC"
    assert heos_mirror.serial_from_entry(None, "Marantz AV 20-MCRR032600573") == "MCRR032600573"
    assert heos_mirror.serial_from_entry(None, None) is None


async def test_find_by_serial(hass: HomeAssistant):
    assert heos_mirror.find_heos_entity(hass, "123456789", "AV 20") is None
    entity_id = add_heos_player(hass)
    assert entity_id == HEOS_ID
    assert heos_mirror.find_heos_entity(hass, "123456789", None) == HEOS_ID
    assert heos_mirror.find_heos_entity(hass, "OTHER", None) is None


async def test_find_by_name_without_serial(hass: HomeAssistant):
    add_heos_player(hass, serial=None)
    # Name matched without the trailing space HEOS adds.
    assert heos_mirror.find_heos_entity(hass, "123456789", "AV 20") == HEOS_ID


def make_device(hass: HomeAssistant, source: str = "HEOS Music") -> DenonDevice:
    receiver = MagicMock()
    receiver.zone = "Main"
    receiver.name = "AV 20"
    receiver.power = "ON"
    receiver.state = "on"
    receiver.input_func = source
    receiver.playing_func_list = []
    receiver.title = receiver.artist = receiver.album = None
    device = DenonDevice(receiver, "123456789-Main", make_entry(), False)
    device.hass = hass
    device._heos_entity_id = HEOS_ID
    return device


async def test_mirrors_heos_while_playing(hass: HomeAssistant):
    hass.states.async_set(HEOS_ID, "playing", PLAYING)
    device = make_device(hass)
    assert device.state == "playing"
    assert device.media_title == "Paint It, Black"
    assert device.media_artist == "Ciara"
    assert device.media_album_name == "Paint It, Black"
    assert device.media_image_url == ART
    assert device.media_duration == 215
    assert device.media_position == 42
    assert device.media_position_updated_at == PLAYING["media_position_updated_at"]
    assert device.extra_state_attributes["heos_entity_id"] == HEOS_ID


async def test_no_mirror_for_other_inputs(hass: HomeAssistant):
    hass.states.async_set(HEOS_ID, "playing", PLAYING)
    device = make_device(hass, source="APPLE TV")
    assert device.state == "on"
    assert device.media_title == "APPLE TV"
    assert device.media_image_url is None
    assert device.media_duration is None


async def test_no_mirror_when_heos_idle_or_receiver_off(hass: HomeAssistant):
    hass.states.async_set(HEOS_ID, "idle", PLAYING)
    device = make_device(hass)
    assert device.media_image_url is None

    hass.states.async_set(HEOS_ID, "paused", PLAYING)
    assert device.state == "paused"
    device._receiver.power = "STANDBY"
    device._receiver.state = "off"
    assert device.state == "off"
    assert device.media_image_url is None


async def test_relative_picture_not_used(hass: HomeAssistant):
    attrs = dict(PLAYING, entity_picture="/api/media_player_proxy/x?token=y")
    hass.states.async_set(HEOS_ID, "playing", attrs)
    assert make_device(hass).media_image_url is None
