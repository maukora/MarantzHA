"""Receiver firmware version, taken from the HEOS device.

The receiver's own API (telnet and the AppCommand XML) doesn't report the
firmware version, but the core HEOS integration does: it stores the
version as sw_version on the receiver's HEOS device. This sensor finds that
device (same match as the HEOS mirror: serial number, else name), shows the
version and follows registry updates. It also copies the version onto this
integration's device, so the device page shows it. Nothing here talks to
the receiver.
"""

from __future__ import annotations

from typing import override

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.start import async_at_started

from denonavr import DenonAVR

from . import DenonavrConfigEntry, heos_mirror
from .const import CONF_SERIAL_NUMBER
from .entity import DenonTelnetEntity

FIRMWARE_VERSION = "firmware_version"


def heos_device_id(hass: HomeAssistant, serial: str | None, name: str | None) -> str | None:
    """Device id of the receiver's HEOS device, or None."""
    entity_id = heos_mirror.find_heos_entity(hass, serial, name)
    if entity_id is None:
        return None
    entry = er.async_get(hass).async_get(entity_id)
    return entry.device_id if entry else None


class DenonFirmwareSensor(DenonTelnetEntity, SensorEntity):
    """Firmware version of the receiver (from the HEOS device)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, FIRMWARE_VERSION)
        self._serial = heos_mirror.serial_from_entry(
            config_entry.data.get(CONF_SERIAL_NUMBER), config_entry.unique_id
        )
        self._heos_device_id: str | None = None
        self._attr_native_value: str | None = None

    @property
    @override
    def available(self) -> bool:
        # Not tied to telnet: the version comes from the device registry.
        return self._attr_native_value is not None

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # HEOS may load after this integration, so look once HA has started.
        self.async_on_remove(async_at_started(self.hass, self._async_link_heos))

    async def _async_link_heos(self, _hass: HomeAssistant) -> None:
        device_id = heos_device_id(self.hass, self._serial, self._receiver.name)
        if device_id is None:
            return
        self._heos_device_id = device_id

        @callback
        def _is_heos_device(event_data: dr.EventDeviceRegistryUpdatedData) -> bool:
            return event_data.get("device_id") == device_id

        self.async_on_remove(
            self.hass.bus.async_listen(
                dr.EVENT_DEVICE_REGISTRY_UPDATED,
                self._heos_device_updated,
                event_filter=_is_heos_device,
            )
        )
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _heos_device_updated(self, _event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        if self._refresh():
            self.async_write_ha_state()

    def _refresh(self) -> bool:
        """Read the version from the HEOS device; return True if it changed."""
        dev_reg = dr.async_get(self.hass)
        heos = dev_reg.async_get(self._heos_device_id) if self._heos_device_id else None
        version = heos.sw_version if heos else None
        changed = version != self._attr_native_value
        self._attr_native_value = version
        own_id = self.registry_entry.device_id if self.registry_entry else None
        own = dev_reg.async_get(own_id) if own_id else None
        if version and own and own.sw_version != version:
            dev_reg.async_update_device(own.id, sw_version=version)
        return changed

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        return False
