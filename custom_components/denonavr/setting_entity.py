"""Base for entities that follow one audio setting line (see audio_settings)."""

from typing import Any, override

from homeassistant.exceptions import HomeAssistantError

from denonavr import DenonAVR
from denonavr.exceptions import DenonAvrError

from . import DenonavrConfigEntry
from .audio_settings import parse_setting
from .entity import DenonTelnetEntity


async def async_send(receiver: DenonAVR, *commands: str) -> None:
    """Send commands over the integration's telnet connection.

    The receiver answers with the new value, which updates the entity.
    """
    try:
        await receiver.async_send_telnet_commands(*commands)
    except DenonAvrError as err:
        raise HomeAssistantError(f"Could not send {', '.join(commands)}: {err}") from err


class DenonSettingEntity(DenonTelnetEntity):
    """Keeps the last value of one setting, parsed from pushed lines."""

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        key: str,
        events: tuple[str, ...],
    ) -> None:
        """Initialize the entity."""
        super().__init__(receiver, config_entry, key)
        self._key = key
        self._telnet_events = events
        self._value: Any = None

    @override
    def _handle_event(self, event: str, parameter: str) -> bool:
        parsed = parse_setting(event, parameter)
        if parsed is None or parsed[0] != self._key or parsed[1] == self._value:
            return False
        self._value = parsed[1]
        return True

    async def _async_send(self, *commands: str) -> None:
        await async_send(self._receiver, *commands)
