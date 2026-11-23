"""Per-speaker level, delay and distance sensors, created as the receiver reports them."""

from typing import Any, override

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR

from . import DenonavrConfigEntry
from .entity import DenonTelnetEntity
from .speakers import (
    DELAY,
    DISTANCE,
    DISTANCE_STEP,
    LEVEL,
    channel_name,
    delay_ms,
    distance_m,
    is_subwoofer,
    parse_speaker,
    relative_distances,
)

UNIQUE_ID_MARK = "-speaker_"
KINDS = (LEVEL, DELAY, DISTANCE)


def _unique_suffix(kind: str, channel: str) -> str:
    return f"speaker_{kind}_{channel.lower()}"


class SpeakerHub:
    """Keep the latest speaker values and add sensors for new speakers.

    A speaker gets sensors once the receiver reports a distance/delay line for
    it, since those are only sent for configured speakers. Whether the
    numbers are distances (Dirac Off) or delays (Dirac filter) is only known
    from the SSSDESTP line that ends the block.
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
        self.raw_distances: dict[str, int] = {}
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
            if kind in KINDS and channel:
                channels.add(channel.upper())
        for channel in sorted(channels):
            self._add_speaker(channel)
        self._receiver.register_callback("SS", self._callback)
        self._entry.async_on_unload(
            lambda: self._receiver.unregister_callback("SS", self._callback)
        )

    def delay(self, channel: str) -> float | None:
        """Delay in ms for a channel, if the receiver reports delays."""
        return delay_ms(self.raw_distances.get(channel), self.distance_step)

    def distance(self, channel: str) -> float | None:
        """Distance in m for a channel, if the receiver reports distances."""
        return distance_m(self.raw_distances.get(channel), self.distance_step)

    def relative_distances(self) -> dict[str, float]:
        """Extra acoustic distance vs the closest speaker, from the delays."""
        delays = {ch: d for ch in self.raw_distances if (d := self.delay(ch)) is not None}
        return relative_distances(delays)

    def _add_speaker(self, channel: str) -> None:
        new = []
        for kind in KINDS:
            if (kind, channel) not in self._entities:
                entity = SpeakerSensor(self, self._receiver, self._entry, kind, channel)
                self._entities[(kind, channel)] = entity
                new.append(entity)
        if new:
            self._add(new)

    def _write(self, kinds: tuple[str, ...], channel: str | None = None) -> None:
        for (kind, ch), entity in self._entities.items():
            if kind in kinds and (channel is None or ch == channel) and entity.hass is not None:
                entity.async_write_ha_state()

    def _callback(self, zone: str, event: str, parameter: str) -> None:
        if zone != self._receiver.zone:
            return
        parsed = parse_speaker(event, parameter)
        if parsed is None:
            return
        if parsed.kind == DISTANCE_STEP:
            # End of the block: units are known now, and relative distances
            # depend on every speaker, so refresh all of them.
            self.distance_step = str(parsed.value)
            self._write((DELAY, DISTANCE))
            return
        channel = parsed.channel
        assert channel is not None
        if parsed.kind == LEVEL:
            self.levels[channel] = parsed.value
            self._write((LEVEL,), channel)
            return
        self.raw_distances[channel] = parsed.value
        if (DISTANCE, channel) not in self._entities:
            self._add_speaker(channel)
        else:
            self._write((DELAY, DISTANCE), channel)


class SpeakerSensor(DenonTelnetEntity, RestoreSensor):
    """Channel level (dB), delay (ms) or distance (m) for one speaker."""

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
        elif kind == DELAY:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
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

    def _live_value(self) -> float | None:
        if self._kind == LEVEL:
            return self._hub.levels.get(self._channel)
        if self._kind == DELAY:
            return self._hub.delay(self._channel)
        return self._hub.distance(self._channel)

    def _has_live_data(self) -> bool:
        if self._kind == LEVEL:
            return self._channel in self._hub.levels
        return self._channel in self._hub.raw_distances and self._hub.distance_step is not None

    @property
    @override
    def native_value(self) -> float | None:
        # Until the receiver sends this speaker's values, show the last ones.
        if not self._has_live_data():
            return self._restored
        return self._live_value()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"channel": self._channel}
        if self._kind == DELAY and not is_subwoofer(self._channel):
            relative = self._hub.relative_distances().get(self._channel)
            if relative is not None:
                attrs["relative_acoustic_distance_m"] = relative
        return attrs
