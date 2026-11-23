"""Binary sensors for Denon AVR receivers (telnet)."""

from typing import Any, override

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR

from . import DenonavrConfigEntry
from .audio_settings import AUTO_LIP_SYNC
from .av_status import dirac_effective
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonTelnetEntity
from .setting_entity import DenonSettingEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    receiver = config_entry.runtime_data
    async_add_entities(
        [
            DenonDiracEffectiveSensor(receiver, config_entry),
            DenonSetupMenuSensor(receiver, config_entry),
            DenonAutoLipSyncSensor(receiver, config_entry),
        ]
    )


class DenonDiracEffectiveSensor(DenonTelnetEntity, BinarySensorEntity):
    """On when a Dirac Live filter is really applied.

    Off when Dirac is off, or in Direct/Pure Direct where only distances and
    levels apply.
    """

    _telnet_events = ("PS", "MS", "PW", "ZM")

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, "dirac_effective")

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        return event in ("MS", "PW", "ZM") or parameter.startswith("DIRAC")

    @property
    @override
    def is_on(self) -> bool | None:
        if self._receiver.power is not None and self._receiver.power != "ON":
            return False  # standby: nothing is playing through Dirac
        return dirac_effective(self._receiver.dirac.dirac_filter, self._receiver.sound_mode_raw)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dirac_filter": self._receiver.dirac.dirac_filter,
            "sound_mode_raw": self._receiver.sound_mode_raw,
        }


class DenonSetupMenuSensor(DenonTelnetEntity, BinarySensorEntity):
    """On while the receiver's setup menu is open on screen."""

    _telnet_events = ("MN",)
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, "setup_menu")

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        return parameter.startswith("MEN")

    @property
    @override
    def is_on(self) -> bool | None:
        return self._receiver.settings_menu


class DenonAutoLipSyncSensor(DenonSettingEntity, BinarySensorEntity):
    """Auto lip sync (from the TV over HDMI) on or off."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, AUTO_LIP_SYNC, ("OP",))

    @property
    @override
    def is_on(self) -> bool | None:
        return self._value
