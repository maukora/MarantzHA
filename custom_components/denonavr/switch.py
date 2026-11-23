"""Switch entities for audio settings."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR

from . import DenonavrConfigEntry
from .audio_settings import TONE_CONTROL
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .setting_entity import DenonSettingEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    async_add_entities([DenonToneControlSwitch(config_entry.runtime_data, config_entry)])


class DenonToneControlSwitch(DenonSettingEntity, SwitchEntity):
    """Tone control: bass and treble only apply while it is on."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(receiver, config_entry, TONE_CONTROL, ("PS",))

    @property
    @override
    def is_on(self) -> bool | None:
        return self._value

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_send("PSTONE CTRL ON")

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_send("PSTONE CTRL OFF")
