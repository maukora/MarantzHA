"""Per-speaker level and distance sensors, created as the receiver reports them."""

from typing import Any, override

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR

from . import DenonavrConfigEntry
from .entity import DenonTelnetEntity
from .speakers import DISTANCE, DISTANCE_STEP, LEVEL, channel_name, parse_speaker

UNIQUE_ID_MARK = "-speaker_"


def _unique_suffix(kind: str, channel: str) -> str:
    return f"speaker_{kind}_{channel.lower()}"


class SpeakerHub:
    """Keep the latest levels/distances and add sensors for new speakers.

    A speaker gets sensors once the receiver reports a distance for it, since
    distances are only sent for configured speakers.
    """

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
        self.levels: dict[str, float] = {}
        self.distances: dict[str, float] = {}
        self.distance_step: str | None = None
        self._entities: dict[tuple[str, str], SpeakerSensor] = {}

    @callback
    def async_start(self) -> None:
        """Recreate sensors known from earlier runs and start listening."""
        registry = er.async_get(self._hass)
        channels = set()
        for entry in er.async_entries_for_config_entry(registry, self._entry.entry_id):
            if entry.domain != "sensor" or UNIQUE_ID_MARK not in (entry.unique_id or ""):
                continue
            suffix = entry.unique_id.rsplit(UNIQUE_ID_MARK, 1)[1]
            kind, _, channel = suffix.partition("_")
            if kind in (LEVEL, DISTANCE) and channel:
                channels.add(channel.upper())
        for channel in sorted(channels):
            self._add_speaker(channel)
        self._receiver.register_callback("SS", self._callback)
        self._entry.async_on_unload(
            lambda: self._receiver.unregister_callback("SS", self._callback)
        )

    def _add_speaker(self, channel: str) -> None:
        new = []
        for kind in (LEVEL, DISTANCE):
            if (kind, channel) not in self._entities:
                entity = SpeakerSensor(self, self._receiver, self._entry, kind, channel)
                self._entities[(kind, channel)] = entity
                new.append(entity)
        if new:
            self._add(new)

    def _callback(self, zone: str, event: str, parameter: str) -> None:
        if zone != self._receiver.zone:
            return
        parsed = parse_speaker(event, parameter)
        if parsed is None:
            return
        if parsed.kind == DISTANCE_STEP:
            if self.distance_step != parsed.value:
                self.distance_step = str(parsed.value)
                for (kind, _), entity in self._entities.items():
                    if kind == DISTANCE and entity.hass is not None:
                        entity.async_write_ha_state()
            return
        channel = parsed.channel
        assert channel is not None
        if parsed.kind == LEVEL:
            self.levels[channel] = parsed.value
        else:
            self.distances[channel] = parsed.value
            if (DISTANCE, channel) not in self._entities:
                self._add_speaker(channel)
                return
        entity = self._entities.get((parsed.kind, channel))
        if entity is not None and entity.hass is not None:
            entity.async_write_ha_state()


class SpeakerSensor(DenonTelnetEntity, RestoreSensor):
    """Channel level (dB) or speaker distance (m) for one speaker."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hub: SpeakerHub,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        kind: str,
        channel: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, _unique_suffix(kind, channel))
        # One translation per kind, with the channel name as a placeholder.
        self._attr_translation_key = f"speaker_{kind}"
        self._attr_translation_placeholders = {"channel": channel_name(channel)}
        self._hub = hub
        self._kind = kind
        self._channel = channel
        self._restored: float | None = None
        if kind == LEVEL:
            self._attr_native_unit_of_measurement = "dB"
            self._attr_suggested_display_precision = 1
        else:
            self._attr_device_class = SensorDeviceClass.DISTANCE
            self._attr_native_unit_of_measurement = UnitOfLength.METERS
            self._attr_suggested_display_precision = 2

    @override
    async def async_added_to_hass(self) -> None:
        # The hub owns the telnet callback; only restore the last value here.
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            value = last.native_value
            self._restored = float(value) if isinstance(value, (int, float)) else None

    @property
    @override
    def native_value(self) -> float | None:
        values = self._hub.levels if self._kind == LEVEL else self._hub.distances
        return values.get(self._channel, self._restored)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"channel": self._channel}
        if self._kind == DISTANCE and self._hub.distance_step is not None:
            attrs["distance_step"] = self._hub.distance_step
        return attrs
