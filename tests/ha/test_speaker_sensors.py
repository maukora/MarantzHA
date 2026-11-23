"""Per-speaker level/distance sensors, fed with the captured AV 20 dump."""

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..test_dirac_slots import received_lines
from .test_select import FakeReceiver, make_entry, setup

CAPTURE = Path(__file__).resolve().parents[2] / "captures" / "20261122-2227-first-probe.log"


def replay_until_second_dump(receiver: FakeReceiver) -> None:
    """Push capture lines up to the end of the 2nd dump (after switching to slot 1)."""
    steps = 0
    for line in received_lines(CAPTURE):
        if line.startswith(("SS", "PSDIRAC")):
            receiver.push(line)
        if line.startswith("SSSDESTP"):
            steps += 1
            if steps == 2:
                return


async def test_sensors_created_from_dump(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert hass.states.get("sensor.av_20_front_left_distance") is None

    replay_until_second_dump(receiver)
    await hass.async_block_till_done()

    # Slot 1 active: the numbers are Dirac delays, not distances.
    delay = hass.states.get("sensor.av_20_front_left_delay")
    assert delay.state == "12.1"
    assert delay.attributes["unit_of_measurement"] == "ms"
    # SL has the largest delay (13.1 ms): FL is (13.1 - 12.1) * 0.343 m farther.
    assert delay.attributes["relative_acoustic_distance_m"] == 0.34
    assert hass.states.get("sensor.av_20_surround_left_delay").attributes[
        "relative_acoustic_distance_m"
    ] == 0.0
    sub = hass.states.get("sensor.av_20_subwoofer_delay")
    assert sub.state == "0.0"
    assert "relative_acoustic_distance_m" not in sub.attributes
    assert hass.states.get("sensor.av_20_front_left_distance").state == "unknown"
    assert hass.states.get("sensor.av_20_front_left_level").state == "2.0"
    # Only configured speakers get sensors (15 speakers x level + delay + distance).
    speaker_ids = [
        e for e in hass.states.async_entity_ids("sensor")
        if e.endswith(("_level", "_distance", "_delay"))
        and not e.endswith("audio_delay")
    ]
    assert len(speaker_ids) == 45
    assert hass.states.get("sensor.av_20_top_front_left_level") is None

    # Live update of an existing sensor.
    receiver.push("SSLEVFL 505")
    assert hass.states.get("sensor.av_20_front_left_level").state == "0.5"


async def test_dirac_off_shows_distances(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    # First dump in the capture: Dirac Off, values in cm.
    for line in received_lines(CAPTURE):
        if line.startswith("SS"):
            receiver.push(line)
        if line.startswith("SSSDESTP"):
            break
    await hass.async_block_till_done()
    dist = hass.states.get("sensor.av_20_front_left_distance")
    assert dist.state == "2.6"
    assert dist.attributes["unit_of_measurement"] == "m"
    assert hass.states.get("sensor.av_20_front_left_delay").state == "unknown"


async def test_sensors_recreated_after_restart(hass: HomeAssistant, receiver: FakeReceiver):
    entry = make_entry()
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", "denonavr", "123456789-speaker_distance_fl", config_entry=entry,
        suggested_object_id="av_20_front_left_distance",
    )
    await setup(hass, receiver, entry)
    # Recreated before any dump arrives (value restored or unknown).
    assert hass.states.get("sensor.av_20_front_left_distance") is not None
    assert hass.states.get("sensor.av_20_front_left_level") is not None


async def test_unload_unregisters_hub(hass: HomeAssistant, receiver: FakeReceiver):
    entry = make_entry()
    await setup(hass, receiver, entry)
    before = len(receiver.callbacks["SS"])
    assert before > 0
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert receiver.callbacks["SS"] == []
