"""Per-speaker level/distance sensors, fed with the captured AV 20 dump."""

from datetime import timedelta
from pathlib import Path

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import restore_state as rs
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
)

from ..test_dirac_slots import received_lines
from .test_select import FakeReceiver, make_entry, setup

CAPTURE = Path(__file__).resolve().parents[2] / "captures" / "20261122-2227-first-probe.log"


def finish_startup_query(receiver: FakeReceiver) -> None:
    """End the answer to the SSSDE ? query sent at setup (no speakers in it)."""
    receiver.push("SSSDE END")


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
    finish_startup_query(receiver)
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
    # Distances don't apply with a Dirac filter: unavailable and hidden.
    assert hass.states.get("sensor.av_20_front_left_distance").state == "unavailable"
    registry = er.async_get(hass)
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by == "integration"
    assert registry.async_get("sensor.av_20_front_left_delay").hidden_by is None
    assert registry.async_get("sensor.av_20_front_left_level").hidden_by is None
    assert hass.states.get("sensor.av_20_front_left_level").state == "2.0"
    # Only configured speakers get sensors (15 speakers x level + delay + distance).
    speaker_ids = [
        e for e in hass.states.async_entity_ids("sensor")
        if e.endswith(("_level", "_distance", "_delay"))
        and not e.endswith(("audio_delay", "lip_sync_delay"))
    ]
    assert len(speaker_ids) == 45
    assert hass.states.get("sensor.av_20_top_front_left_level") is None

    # Live update of an existing sensor.
    receiver.push("SSLEVFL 505")
    assert hass.states.get("sensor.av_20_front_left_level").state == "0.5"


async def test_dirac_off_shows_distances(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    finish_startup_query(receiver)
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
    # Dirac Off: delays are hidden instead.
    assert hass.states.get("sensor.av_20_front_left_delay").state == "unavailable"
    registry = er.async_get(hass)
    assert registry.async_get("sensor.av_20_front_left_delay").hidden_by == "integration"
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by is None


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


async def test_delays_restored_in_their_unit(hass: HomeAssistant, receiver: FakeReceiver):
    entry = make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    ids = {}
    for kind in ("delay", "distance"):
        for ch in ("fl", "sl"):
            object_id = f"av_20_{'front' if ch == 'fl' else 'surround'}_left_{kind}"
            ids[object_id] = registry.async_get_or_create(
                "sensor", "denonavr", f"123456789-speaker_{kind}_{ch}", config_entry=entry,
                suggested_object_id=object_id,
            ).id
    mock_restore_cache(
        hass,
        [
            State("sensor.av_20_front_left_delay", "12.1",
                  {"raw_value": 121, "distance_step": "01S"}),
            State("sensor.av_20_surround_left_delay", "13.1",
                  {"raw_value": 131, "distance_step": "01S"}),
            # Saved by an older version: no unit, so it is not trusted.
            State("sensor.av_20_front_left_distance", "1.21", {}),
        ],
    )
    data = hass.data[rs.DATA_RESTORE_STATE]
    if hasattr(data, "last_states_by_entity_registry_id"):
        data.last_states_by_entity_registry_id = {
            ids[eid.split(".")[1]]: st for eid, st in data.last_states.items()
        }
    await setup(hass, receiver, entry)
    await hass.async_block_till_done()

    delay = hass.states.get("sensor.av_20_front_left_delay")
    assert delay.state == "12.1"
    assert delay.attributes["relative_acoustic_distance_m"] == 0.34
    assert hass.states.get("sensor.av_20_front_left_distance").state == "unavailable"
    registry = er.async_get(hass)
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by == "integration"

    # A new dump replaces the restored values.
    finish_startup_query(receiver)
    receiver.push("SSSDEFL 0260")
    receiver.push("SSSDESTP 01M")
    assert hass.states.get("sensor.av_20_front_left_distance").state == "2.6"
    assert hass.states.get("sensor.av_20_front_left_delay").state == "unavailable"
    # Shown again once it applies; a user's own hide is left alone.
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by is None
    registry.async_update_entity(
        "sensor.av_20_front_left_distance", hidden_by=er.RegistryEntryHider.USER
    )
    receiver.push("SSSDEFL 0121")
    receiver.push("SSSDESTP 01S")
    await hass.async_block_till_done()
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by == "user"
    receiver.push("SSSDESTP 01M")
    assert registry.async_get("sensor.av_20_front_left_distance").hidden_by == "user"


QUERY = Path(__file__).resolve().parents[2] / "captures" / "20261123-1750-sssde-query-ha-log.log"


async def test_query_answer_updates_known_speakers_only(
    hass: HomeAssistant, receiver: FakeReceiver
):
    entry = make_entry()
    entry.add_to_hass(hass)
    # FL and SL are known from an earlier run.
    for ch, name in (("fl", "front_left"), ("sl", "surround_left")):
        er.async_get(hass).async_get_or_create(
            "sensor", "denonavr", f"123456789-speaker_delay_{ch}", config_entry=entry,
            suggested_object_id=f"av_20_{name}_delay",
        )
    await setup(hass, receiver, entry)
    # Setup asks for the delays once; the answer follows.
    receiver.async_send_telnet_commands.assert_any_await("SSSDE ?")
    receiver.async_send_telnet_commands.assert_any_await("SSSPC ?")
    for line in received_lines(QUERY):
        receiver.push(line)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.av_20_front_left_delay").state == "12.1"
    assert hass.states.get("sensor.av_20_surround_left_delay").state == "13.1"
    # Channels that only appear in the query answer get no sensors.
    assert hass.states.get("sensor.av_20_front_right_delay") is None
    assert hass.states.get("sensor.av_20_top_front_left_delay") is None
    # Relative distance only from the known speakers.
    assert hass.states.get("sensor.av_20_front_left_delay").attributes[
        "relative_acoustic_distance_m"
    ] == 0.34

    # After the query, pushed lines add speakers again.
    receiver.push("SSSDEFR 0119")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.av_20_front_right_delay").state == "11.9"


async def test_unconfigured_speakers_from_old_version_removed(
    hass: HomeAssistant, receiver: FakeReceiver
):
    entry = make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    ids = {}
    for kind in ("level", "delay", "distance"):
        for ch, name in (("fl", "front_left"), ("tfl", "top_front_left")):
            object_id = f"av_20_{name}_{kind}"
            ids[object_id] = registry.async_get_or_create(
                "sensor", "denonavr", f"123456789-speaker_{kind}_{ch}", config_entry=entry,
                suggested_object_id=object_id,
            ).id
    mock_restore_cache(
        hass,
        [
            State("sensor.av_20_front_left_delay", "12.1",
                  {"raw_value": 121, "distance_step": "01S"}),
            State("sensor.av_20_top_front_left_delay", "30.0",
                  {"raw_value": 300, "distance_step": "01S"}),
            State("sensor.av_20_top_front_left_distance", "unknown",
                  {"raw_value": 300, "distance_step": "01S"}),
        ],
    )
    data = hass.data[rs.DATA_RESTORE_STATE]
    if hasattr(data, "last_states_by_entity_registry_id"):
        data.last_states_by_entity_registry_id = {
            ids[eid.split(".")[1]]: st for eid, st in data.last_states.items()
        }
    await setup(hass, receiver, entry)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=10))
    await hass.async_block_till_done()

    assert hass.states.get("sensor.av_20_front_left_delay").state == "12.1"
    for kind in ("level", "delay", "distance"):
        assert registry.async_get(f"sensor.av_20_top_front_left_{kind}") is None
        assert hass.states.get(f"sensor.av_20_top_front_left_{kind}") is None
    assert registry.async_get("sensor.av_20_front_left_level") is not None


async def test_speaker_layout(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    finish_startup_query(receiver)
    assert hass.states.get("sensor.av_20_speaker_layout").state == "unknown"

    replay_until_second_dump(receiver)
    receiver.push("OPINFASP 22121111011000011000000000000000")
    await hass.async_block_till_done()

    layout = hass.states.get("sensor.av_20_speaker_layout")
    # Markus's AV 20: 7 ear-level, 4 subwoofer outputs, 4 heights.
    assert layout.state == "7.4.4"
    speakers = {s["channel"]: s for s in layout.attributes["speakers"]}
    assert list(speakers)[:3] == ["FL", "FR", "C"]
    assert layout.attributes["speaker_count"] == 15
    fl = speakers["FL"]
    assert fl["group"] == "front"
    assert fl["azimuth"] == -30 and fl["x"] == -0.5 and fl["y"] == 0.87
    assert fl["playing"] is True
    assert fl["level_db"] == 2.0
    assert fl["delay_ms"] == 12.1
    assert fl["relative_distance_m"] == 0.34
    assert speakers["C"]["playing"] is False
    assert speakers["SW2"]["playing"] is True  # all subs share one digit
    assert speakers["FHL"]["group"] == "height"
    assert speakers["FHL"]["playing"] is False
    assert layout.attributes["playing_count"] == 6  # FL, FR + 4 sub outputs
    assert layout.attributes["subwoofers"] is None

    # The speaker config says one subwoofer: the unused outputs go away.
    receiver.push("SSSPCSWF 1SP")
    await hass.async_block_till_done()
    layout = hass.states.get("sensor.av_20_speaker_layout")
    assert layout.state == "7.1.4"
    assert layout.attributes["subwoofers"] == 1
    assert layout.attributes["speaker_count"] == 12
    assert layout.attributes["playing_count"] == 3
    assert hass.states.get("sensor.av_20_subwoofer_delay") is not None
    assert hass.states.get("sensor.av_20_subwoofer_2_delay") is None
    assert er.async_get(hass).async_get("sensor.av_20_subwoofer_3_level") is None

    # Later SSSDE lines for the unused outputs don't bring them back.
    receiver.push("SSSDESW4 0000")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.av_20_subwoofer_4_delay") is None


def test_sub_count_parsing():
    from custom_components.denonavr.speakers import SUB_COUNT, parse_line, sub_index

    assert parse_line("SSSPCSWF 1SP").kind == SUB_COUNT
    assert parse_line("SSSPCSWF 1SP").value == 1
    assert parse_line("SSSPCSWF NO").value == 0
    assert parse_line("SSSPCSWL 2LR") is None
    assert parse_line("SSSPCFRO YES") is None
    assert [sub_index(c) for c in ("SW", "SW2", "SW4", "FL")] == [1, 2, 4, 0]


def test_layout_names():
    from custom_components.denonavr.layout import layout_name, playing_channels

    assert layout_name({"FL", "FR", "C", "SL", "SR", "SW"}) == "5.1"
    assert layout_name({"FL", "FR", "C", "SL", "SR", "SBL", "SBR", "SW",
                        "FHL", "FHR", "RHL", "RHR"}) == "7.1.4"
    assert layout_name(set()) is None
    assert playing_channels("22222222022000022000000000000000") == {
        "FL", "FR", "C", "SW", "SW2", "SW3", "SW4", "SL", "SR", "SBL", "SBR",
        "FHL", "FHR", "RHL", "RHR",
    }
