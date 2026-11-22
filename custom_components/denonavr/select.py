"""Select entities for Denon AVR receivers (Dirac Live filter slot)."""

from __future__ import annotations

import logging
from typing import Any, override

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_TYPE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from denonavr import DenonAVR
from denonavr.const import ALL_ZONES
from denonavr.exceptions import AvrCommandError, DenonAvrError

from . import DenonavrConfigEntry
from .const import CONF_MANUFACTURER, CONF_USE_TELNET, DEFAULT_USE_TELNET, DOMAIN
from .dirac_slots import DiracSlotTracker

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities.

    The Dirac filter is only reported over telnet, so the entity is only
    created when the integration uses telnet.
    """
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    async_add_entities([DenonDiracFilterSelect(config_entry.runtime_data, config_entry)])


class DenonDiracFilterSelect(SelectEntity, RestoreEntity):
    """Active Dirac Live filter slot, labelled with the filter names."""

    _attr_has_entity_name = True
    _attr_translation_key = "dirac_filter"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the entity."""
        device_id = config_entry.unique_id or config_entry.entry_id
        self._attr_unique_id = f"{device_id}-dirac_filter"
        # Same identifiers as the media player, so this lands on the same device.
        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{config_entry.data[CONF_HOST]}/",
            hw_version=config_entry.data[CONF_TYPE],
            identifiers={(DOMAIN, device_id)},
            manufacturer=config_entry.data[CONF_MANUFACTURER],
            model=config_entry.data[CONF_MODEL],
            name=receiver.name,
        )
        self._receiver = receiver
        self._slots = DiracSlotTracker()

    @property
    def _lib_value(self) -> str | None:
        return self._receiver.dirac.dirac_filter

    @property
    @override
    def available(self) -> bool:
        return self._receiver.telnet_connected and self._receiver.telnet_healthy

    @property
    @override
    def options(self) -> list[str]:
        return self._slots.options(self._lib_value)

    @property
    @override
    def current_option(self) -> str | None:
        return self._slots.option_for(self._lib_value)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"active_slot": self._lib_value}
        attrs.update(self._slots.as_attributes())
        return attrs

    @override
    async def async_select_option(self, option: str) -> None:
        value = self._slots.lib_value_for(option)
        if value is None:
            raise HomeAssistantError(f"Unknown Dirac filter option: {option}")
        try:
            await self._receiver.dirac.async_dirac_filter(value)
        except (AvrCommandError, DenonAvrError) as err:
            raise HomeAssistantError(f"Could not set Dirac filter: {err}") from err
        # State is written when the receiver confirms with a PSDIRAC event.

    def _ps_callback(self, zone: str, event: str, parameter: str) -> None:
        """Write state when the active Dirac slot changes."""
        if zone not in (self._receiver.zone, ALL_ZONES):
            return
        if parameter.startswith("DIRAC"):
            self.async_write_ha_state()

    def _op_callback(self, zone: str, event: str, parameter: str) -> None:
        """Track slot names; write state at the end of each OPDLS block."""
        if self._slots.handle_op_parameter(parameter):
            self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        """Restore known slot names and register telnet callbacks."""
        await super().async_added_to_hass()
        # The receiver has no known query for slot names, so keep the last ones
        # across HA restarts until the next OPDLS block arrives.
        if (last_state := await self.async_get_last_state()) is not None:
            self._slots.restore_from_attributes(dict(last_state.attributes))
        self._receiver.register_callback("PS", self._ps_callback)
        self._receiver.register_callback("OP", self._op_callback)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Unregister telnet callbacks."""
        self._receiver.unregister_callback("PS", self._ps_callback)
        self._receiver.unregister_callback("OP", self._op_callback)
