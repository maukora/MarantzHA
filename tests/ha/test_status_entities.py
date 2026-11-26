"""Sensors, binary sensors and the dimmer/preset selects, with a fake receiver."""

from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .test_select import FakeReceiver, make_entry, setup


def state(hass: HomeAssistant, entity_id: str) -> str:
    return hass.states.get(entity_id).state


async def test_signal_sensors_follow_pushes(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    receiver.async_send_telnet_commands.assert_any_await("SSINFAISSIG ?", "SSINFAISFSV ?")
    assert state(hass, "sensor.av_20_input_signal") == STATE_UNKNOWN

    for line in [
        "SYSDA Dolby Atmos          ",
        "SYSMI Dolby Atmos",
        "SSINFAISSIG 25",
        "SSINFAISFSV 48K",
        "SSSMG MOV",
    ]:
        receiver.push(line)
    assert state(hass, "sensor.av_20_input_audio_format") == "Dolby Atmos"
    assert state(hass, "sensor.av_20_decoded_mode") == "Dolby Atmos"
    assert state(hass, "sensor.av_20_input_signal") == "Dolby Atmos"
    assert hass.states.get("sensor.av_20_input_signal").attributes["code"] == "25"
    assert state(hass, "sensor.av_20_sample_rate") == "48.0"
    assert hass.states.get("sensor.av_20_sample_rate").attributes[ATTR_UNIT_OF_MEASUREMENT] == "kHz"
    assert state(hass, "sensor.av_20_smart_select_group") == "Movie"

    # Switching to a source with no signal.
    receiver.push("SSINFAISSIG 12")
    receiver.push("SSINFAISFSV NON")
    assert state(hass, "sensor.av_20_input_signal") == "No signal"
    assert state(hass, "sensor.av_20_sample_rate") == STATE_UNKNOWN


async def test_library_backed_sensors(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert state(hass, "sensor.av_20_sound_mode_raw") == "DOLBY ATMOS"
    assert state(hass, "sensor.av_20_audio_delay") == "162"
    receiver.push("MSSTEREO")
    receiver.push("MSSMART0")  # not a sound mode, ignored by the library
    receiver.push("PSDELAY 000")
    assert state(hass, "sensor.av_20_sound_mode_raw") == "STEREO"
    assert state(hass, "sensor.av_20_audio_delay") == "0"


async def test_input_source(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert state(hass, "sensor.av_20_input_source") == "TV Audio"
    receiver.push("SIMPLAY")
    assert state(hass, "sensor.av_20_input_source") == "MPLAY"


async def test_dirac_effective(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    entity_id = "binary_sensor.av_20_dirac_live_active"
    assert state(hass, entity_id) == "on"
    receiver.push("MSDIRECT")
    assert state(hass, entity_id) == "off"
    receiver.push("MSDOLBY ATMOS")
    assert state(hass, entity_id) == "on"
    receiver.push("ZMOFF")
    assert state(hass, entity_id) == "off"
    receiver.push("ZMON")
    assert state(hass, entity_id) == "on"
    receiver.push("PSDIRAC OFF")
    assert state(hass, entity_id) == "off"


async def test_setup_menu(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    entity_id = "binary_sensor.av_20_setup_menu_open"
    assert state(hass, entity_id) == "off"
    receiver.push("MNMEN ON")
    assert state(hass, entity_id) == "on"
    receiver.push("MNMEN OFF")
    assert state(hass, entity_id) == "off"


async def test_dimmer_and_preset(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert state(hass, "select.av_20_display_dimmer") == "Dark"
    assert state(hass, "select.av_20_speaker_preset") == "2"
    receiver.push("DIM BRI")
    receiver.push("SPPR 1")
    assert state(hass, "select.av_20_display_dimmer") == "Bright"
    assert state(hass, "select.av_20_speaker_preset") == "1"

    await hass.services.async_call(
        SELECT_DOMAIN, SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.av_20_display_dimmer", ATTR_OPTION: "Dim"}, blocking=True,
    )
    receiver.async_dimmer.assert_awaited_once_with("Dim")
    await hass.services.async_call(
        SELECT_DOMAIN, SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.av_20_speaker_preset", ATTR_OPTION: "2"}, blocking=True,
    )
    receiver.async_speaker_preset.assert_awaited_once_with(2)


async def test_no_entities_without_telnet(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry(use_telnet=False))
    # Only the firmware version, which comes from the HEOS device, not telnet.
    assert hass.states.async_entity_ids(("sensor", "binary_sensor", "select", "number", "switch")) == [
        "sensor.av_20_firmware_version"
    ]
    receiver.async_send_telnet_commands.assert_not_awaited()
