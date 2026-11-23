"""Number entities for audio settings (sub/LFE/bass/treble, channel trims)."""

from typing import override

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR

from . import DenonavrConfigEntry
from .audio_settings import (
    BASS,
    CHANNEL_VOLUME,
    LFE_LEVEL,
    SUBWOOFER_LEVEL,
    TREBLE,
    encode_level,
    parse_setting,
    tone_code,
)
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonTelnetEntity
from .setting_entity import DenonSettingEntity, async_send
from .speakers import channel_name

PARALLEL_UPDATES = 1
UNIQUE_ID_MARK = "-channel_volume_"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up number entities."""
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    receiver = config_entry.runtime_data
    async_add_entities(
        [
            DenonLevelNumber(receiver, config_entry, SUBWOOFER_LEVEL, -12, 12, 0.5),
            DenonLevelNumber(receiver, config_entry, LFE_LEVEL, -10, 0, 1),
            DenonLevelNumber(receiver, config_entry, BASS, -6, 6, 1),
            DenonLevelNumber(receiver, config_entry, TREBLE, -6, 6, 1),
        ]
    )
    ChannelVolumeHub(hass, receiver, config_entry, async_add_entities).async_start()


class DenonLevelNumber(DenonSettingEntity, NumberEntity):
    """A level in dB: subwoofer, LFE, bass or treble."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "dB"
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        key: str,
        low: float,
        high: float,
        step: float,
    ) -> None:
        """Initialize the entity."""
        super().__init__(receiver, config_entry, key, ("PS",))
        self._attr_native_min_value = low
        self._attr_native_max_value = high
        self._attr_native_step = step

    @property
    @override
    def native_value(self) -> float | None:
        return self._value

    @override
    async def async_set_native_value(self, value: float) -> None:
        if self._key == SUBWOOFER_LEVEL:
            await self._async_send(f"PSSWL {encode_level(value)}")
        elif self._key == LFE_LEVEL:
            await self._async_send(f"PSLFE {-int(value):02d}")
        else:
            # Bass/treble only apply with tone control on (as the library does).
            command = "PSBAS" if self._key == BASS else "PSTRE"
            await self._async_send("PSTONE CTRL ON", f"{command} {tone_code(int(value))}")


class ChannelVolumeHub:
    """Adds a trim number per channel the receiver reports (CV lines)."""

    def __init__(
        self,
        hass: HomeAssistant,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        """Initialize the hub."""
        self._hass = hass
        self._receiver = receiver
        self._entry = config_entry
        self._add = async_add_entities
        self.values: dict[str, float] = {}
        self._entities: dict[str, DenonChannelVolumeNumber] = {}

    def async_start(self) -> None:
        """Recreate trims known from earlier runs and start listening."""
        registry = er.async_get(self._hass)
        for entry in er.async_entries_for_config_entry(registry, self._entry.entry_id):
            if entry.domain == "number" and UNIQUE_ID_MARK in (entry.unique_id or ""):
                self._add_channel(entry.unique_id.rsplit(UNIQUE_ID_MARK, 1)[1].upper())
        self._receiver.register_callback("CV", self._callback)
        self._entry.async_on_unload(
            lambda: self._receiver.unregister_callback("CV", self._callback)
        )

    def _add_channel(self, channel: str) -> None:
        if channel in self._entities:
            return
        entity = DenonChannelVolumeNumber(self, self._receiver, self._entry, channel)
        self._entities[channel] = entity
        self._add([entity])

    def _callback(self, zone: str, event: str, parameter: str) -> None:
        if zone != self._receiver.zone:
            return
        parsed = parse_setting(event, parameter)
        if parsed is None or parsed[0] != CHANNEL_VOLUME:
            return
        channel, level = parsed[1]
        self.values[channel] = level
        if channel not in self._entities:
            self._add_channel(channel)
        elif (entity := self._entities[channel]).hass is not None:
            entity.async_write_ha_state()


class DenonChannelVolumeNumber(DenonTelnetEntity, NumberEntity):
    """Channel volume trim (the remote's per-channel level), -12..+12 dB."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "dB"
    _attr_native_min_value = -12
    _attr_native_max_value = 12
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hub: ChannelVolumeHub,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        channel: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(receiver, config_entry, f"channel_volume_{channel.lower()}")
        self._attr_translation_key = "channel_volume"
        self._attr_translation_placeholders = {"channel": channel_name(channel)}
        self._hub = hub
        self._channel = channel

    @property
    @override
    def native_value(self) -> float | None:
        return self._hub.values.get(self._channel)

    @override
    async def async_set_native_value(self, value: float) -> None:
        await async_send(self._receiver, f"CV{self._channel} {encode_level(value)}")
