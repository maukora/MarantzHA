"""Dirac filter select entity, with a fake receiver (no network)."""

from __future__ import annotations

from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import restore_state as rs
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

# Import first so patch() can find the modules.
import custom_components.denonavr.media_player
import custom_components.denonavr.receiver  # noqa: F401

from ..test_dirac_slots import BLOCK

ENTITY_ID = "select.av_20_dirac_live_filter"
UNIQUE_ID = "123456789-dirac_filter"


class FakeDirac:
    def __init__(self) -> None:
        self.dirac_filter: str | None = "Slot 1"
        self.async_dirac_filter = AsyncMock()


class FakeReceiver:
    """Just enough of denonavr.DenonAVR for the select platform."""

    def __init__(self) -> None:
        self.name = "AV 20"
        self.zone = "Main"
        self.zones = {"Main": self}
        self.telnet_connected = True
        self.telnet_healthy = True
        self.dirac = FakeDirac()
        self.callbacks: dict[str, list] = defaultdict(list)
        # Bits ConnectDenonAVR touches during setup.
        self.manufacturer = "Marantz"
        self.model_name = "AV 20"
        self.receiver_type = "avr-x-2016"
        self.host = "10.1.1.22"
        self.serial_number = "123456789"
        self.set_async_client_getter = MagicMock()
        self.async_setup = AsyncMock()
        self.async_update = AsyncMock()
        self.async_update_audyssey = AsyncMock()
        self.async_telnet_connect = AsyncMock()
        self.async_telnet_disconnect = AsyncMock()

    def register_callback(self, event, callback):
        self.callbacks[event].append(callback)

    def unregister_callback(self, event, callback):
        self.callbacks[event].remove(callback)

    def push(self, line: str) -> None:
        """Simulate a telnet line the way denonavr dispatches it."""
        event, parameter = line[:2], line[2:]
        if line.startswith("PSDIRAC "):
            value = line[8:]
            self.dirac.dirac_filter = {"OFF": "Off"}.get(value, f"Slot {value}")
        for cb in self.callbacks[event]:
            cb("Main", event, parameter)


def make_entry(use_telnet: bool = True) -> MockConfigEntry:
    return MockConfigEntry(
        domain="denonavr",
        unique_id="123456789",
        title="AV 20",
        data={
            "host": "10.1.1.22",
            "model": "AV 20",
            "type": "avr-x-2016",
            "manufacturer": "Marantz",
            "serial_number": "123456789",
        },
        options={"use_telnet": use_telnet},
    )


async def setup(hass: HomeAssistant, receiver: FakeReceiver, entry: MockConfigEntry):
    if hass.config_entries.async_get_entry(entry.entry_id) is None:
        entry.add_to_hass(hass)
    with (
        patch("custom_components.denonavr.receiver.DenonAVR", return_value=receiver),
        patch(
            "custom_components.denonavr.media_player.async_setup_entry",
            AsyncMock(return_value=None),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


@pytest.fixture
def receiver() -> FakeReceiver:
    return FakeReceiver()


async def test_slot_names_from_push(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    state = hass.states.get(ENTITY_ID)
    assert state.state == "Slot 1"
    assert state.attributes[ATTR_OPTIONS] == ["Off", "Slot 1", "Slot 2", "Slot 3"]

    for line in BLOCK:
        receiver.push(line)
    state = hass.states.get(ENTITY_ID)
    assert state.state == "ALeft-HigherLowerShelfs"
    assert state.attributes[ATTR_OPTIONS] == ["Off", "ALeft-HigherLowerShelfs", "ArendalLeft"]
    assert state.attributes["slot_2_name"] == "ArendalLeft"
    assert state.attributes["slot_3_imported"] is False

    receiver.push("PSDIRAC 2")
    assert hass.states.get(ENTITY_ID).state == "ArendalLeft"
    receiver.push("PSDIRAC OFF")
    assert hass.states.get(ENTITY_ID).state == "Off"

    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity.unique_id == UNIQUE_ID


async def test_select_sends_library_value(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    for line in BLOCK:
        receiver.push(line)
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "ArendalLeft"},
        blocking=True,
    )
    receiver.dirac.async_dirac_filter.assert_awaited_once_with("Slot 2")


async def test_names_restored_after_restart(hass: HomeAssistant, receiver: FakeReceiver):
    entry = make_entry()
    entry.add_to_hass(hass)
    reg_entry = er.async_get(hass).async_get_or_create(
        SELECT_DOMAIN, "denonavr", UNIQUE_ID, config_entry=entry,
        suggested_object_id="av_20_dirac_live_filter",
    )
    assert reg_entry.entity_id == ENTITY_ID
    mock_restore_cache(
        hass,
        [State(ENTITY_ID, "ArendalLeft", {
            "slot_1_name": "ALeft-HigherLowerShelfs", "slot_1_imported": True,
            "slot_2_name": "ArendalLeft", "slot_2_imported": True,
            "slot_3_name": None, "slot_3_imported": False,
        })],
    )
    # HA 2026.11 looks stored states up by registry id; the test helper
    # (built for 2026.10) only fills the old index.
    data = hass.data[rs.DATA_RESTORE_STATE]
    if hasattr(data, "last_states_by_entity_registry_id"):
        data.last_states_by_entity_registry_id = {reg_entry.id: data.last_states[ENTITY_ID]}
    receiver.dirac.dirac_filter = "Slot 2"
    await setup(hass, receiver, entry)
    state = hass.states.get(ENTITY_ID)
    assert state.state == "ArendalLeft"
    assert state.attributes[ATTR_OPTIONS] == ["Off", "ALeft-HigherLowerShelfs", "ArendalLeft"]


async def test_unavailable_when_telnet_down(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    receiver.telnet_healthy = False
    receiver.push("PSDIRAC 1")
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_not_created_without_telnet(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry(use_telnet=False))
    assert hass.states.get(ENTITY_ID) is None


async def test_unload_unregisters(hass: HomeAssistant, receiver: FakeReceiver):
    entry = make_entry()
    await setup(hass, receiver, entry)
    assert receiver.callbacks["OP"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not receiver.callbacks["OP"] and not receiver.callbacks["PS"]
