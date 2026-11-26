"""Firmware version sensor, read from the receiver's HEOS device."""

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.denonavr.const import DOMAIN

from .test_select import FakeReceiver, make_entry, setup

SENSOR = "sensor.av_20_firmware_version"


def add_heos_device(hass: HomeAssistant, version: str | None = "3.139.175") -> str:
    heos_entry = MockConfigEntry(domain="heos", title="HEOS System")
    heos_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=heos_entry.entry_id,
        identifiers={("heos", "-1763064440")},
        name="AV 20",
        serial_number="123456789",
        sw_version=version,
    )
    er.async_get(hass).async_get_or_create(
        "media_player", "heos", "-1763064440", config_entry=heos_entry, device_id=device.id
    )
    return device.id


async def test_firmware_from_heos(hass: HomeAssistant, receiver: FakeReceiver):
    heos_id = add_heos_device(hass)
    entry = make_entry()
    await setup(hass, receiver, entry)

    state = hass.states.get(SENSOR)
    assert state.state == "3.139.175"
    assert er.async_get(hass).async_get(SENSOR).entity_category == "diagnostic"
    dev_reg = dr.async_get(hass)
    own = dev_reg.async_get(er.async_get(hass).async_get(SENSOR).device_id)
    assert own.identifiers == {(DOMAIN, entry.unique_id)}
    assert own.sw_version == "3.139.175"

    # A firmware update shows up when HEOS updates its device.
    dev_reg.async_update_device(heos_id, sw_version="3.140.200")
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "3.140.200"
    assert dev_reg.async_get(own.id).sw_version == "3.140.200"

    # Other devices' changes are ignored.
    other = MockConfigEntry(domain="heos")
    other.add_to_hass(hass)
    dev_reg.async_get_or_create(config_entry_id=other.entry_id, identifiers={("heos", "x")}, sw_version="9")
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "3.140.200"


async def test_no_heos_device(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert hass.states.get(SENSOR).state == STATE_UNAVAILABLE


async def test_works_without_telnet(hass: HomeAssistant, receiver: FakeReceiver):
    add_heos_device(hass)
    await setup(hass, receiver, make_entry(use_telnet=False))
    assert hass.states.get(SENSOR).state == "3.139.175"
