"""Sensors for Denon AVR receivers: input signal and sound status (telnet)."""

import logging
from typing import Any, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfFrequency, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from denonavr import DenonAVR
from denonavr.exceptions import DenonAvrError

from . import DenonavrConfigEntry
from .av_status import (
    DECODED_MODE,
    INITIAL_QUERIES,
    INPUT_FORMAT,
    INPUT_SIGNAL,
    SAMPLE_RATE,
    SMART_SELECT_GROUP,
    parse_status,
    signal_name,
)
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonTelnetEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors (telnet only: the values are pushed as events)."""
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    receiver = config_entry.runtime_data
    async_add_entities(
        [
            DenonStatusSensor(receiver, config_entry, INPUT_FORMAT),
            DenonStatusSensor(receiver, config_entry, DECODED_MODE),
            DenonSignalSensor(receiver, config_entry),
            DenonSampleRateSensor(receiver, config_entry),
            DenonStatusSensor(receiver, config_entry, SMART_SELECT_GROUP),
            DenonSoundModeRawSensor(receiver, config_entry),
            DenonAudioDelaySensor(receiver, config_entry),
        ]
    )

    async def _initial_queries() -> None:
        # Read-only "?" queries over the integration's own telnet connection.
        if not receiver.telnet_connected:
            return
        try:
            await receiver.async_send_telnet_commands(*INITIAL_QUERIES)
        except DenonAvrError as err:
            _LOGGER.debug("Initial signal queries failed: %s", err)

    config_entry.async_create_background_task(
        hass, _initial_queries(), "denonavr signal queries"
    )


class DenonStatusSensor(DenonTelnetEntity, SensorEntity):
    """Text sensor fed by one kind of status line (SYSDA, SYSMI, SSSMG ...)."""

    _telnet_events = ("SY", "SS")

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, key)
        self._key = key
        self._value: Any = None

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        parsed = parse_status(event, parameter)
        if parsed is None or parsed[0] != self._key:
            return False
        if parsed[1] == self._value:
            return False
        self._value = parsed[1]
        return True

    @property
    @override
    def native_value(self) -> Any:
        return self._value


class DenonSignalSensor(DenonStatusSensor):
    """Incoming signal type, from the SSINFAISSIG code."""

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, INPUT_SIGNAL)

    @property
    @override
    def native_value(self) -> str | None:
        return signal_name(self._value)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"code": self._value}


class DenonSampleRateSensor(DenonStatusSensor):
    """Input sample rate in kHz (unknown when there is no signal)."""

    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_native_unit_of_measurement = UnitOfFrequency.KILOHERTZ
    _attr_suggested_display_precision = 1

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, SAMPLE_RATE)


class DenonSoundModeRawSensor(DenonTelnetEntity, SensorEntity):
    """Sound mode as the receiver reports it (MS...)."""

    _telnet_events = ("MS",)

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, "sound_mode_raw")

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        return True

    @property
    @override
    def native_value(self) -> str | None:
        return self._receiver.sound_mode_raw


class DenonAudioDelaySensor(DenonTelnetEntity, SensorEntity):
    """Audio delay (lip sync) in ms. Stored per input on the receiver."""

    _telnet_events = ("PS",)
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(receiver, config_entry, "audio_delay")

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        return parameter.startswith("DELAY")

    @property
    @override
    def native_value(self) -> int | None:
        return self._receiver.delay
