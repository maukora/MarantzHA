"""Base entity for push-updated Denon AVR entities (telnet only)."""

from typing import override

from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_TYPE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from denonavr import DenonAVR
from denonavr.const import ALL_ZONES

from . import DenonavrConfigEntry
from .const import CONF_MANUFACTURER, DOMAIN


class DenonTelnetEntity(Entity):
    """An entity on the receiver's device, updated by telnet events.

    Subclasses list the telnet events they care about in ``_telnet_events``
    and decide in ``_handle_event`` whether the state changed.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _telnet_events: tuple[str, ...] = ()

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry, key: str) -> None:
        """Initialize the entity."""
        device_id = config_entry.unique_id or config_entry.entry_id
        self._attr_unique_id = f"{device_id}-{key}"
        self._attr_translation_key = key
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

    @property
    @override
    def available(self) -> bool:
        return self._receiver.telnet_connected and self._receiver.telnet_healthy

    def _handle_event(self, event: str, parameter: str) -> bool:
        """Process an event; return True when state should be written."""
        raise NotImplementedError

    def _telnet_callback(self, zone: str, event: str, parameter: str) -> None:
        if zone not in (self._receiver.zone, ALL_ZONES):
            return
        if self._handle_event(event, parameter):
            self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for event in self._telnet_events:
            self._receiver.register_callback(event, self._telnet_callback)

    @override
    async def async_will_remove_from_hass(self) -> None:
        for event in self._telnet_events:
            self._receiver.unregister_callback(event, self._telnet_callback)
