"""Audio setting entities: values from pushed lines, commands sent on change."""

from homeassistant.core import HomeAssistant

from .test_select import FakeReceiver, make_entry, setup


def state(hass: HomeAssistant, entity_id: str):
    return hass.states.get(entity_id)


async def call(hass, domain, service, entity_id, **data):
    await hass.services.async_call(
        domain, service, {"entity_id": entity_id, **data}, blocking=True
    )


async def test_values_follow_pushes(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    # Read-only queries for the current values are sent once.
    receiver.async_send_telnet_commands.assert_any_await(
        "PSSWL ?", "PSLFE ?", "PSBAS ?", "PSTRE ?", "PSTONE CTRL ?", "PSDRC ?", "CV?"
    )
    for line in ("PSSWL 46", "PSLFE 00", "PSBAS 50", "PSTRE 52", "PSTONE CTRL OFF",
                 "PSDRC OFF", "OPALSSET ON", "OPALSVAL 000",
                 "OPINFASP 22121111011000011000000000000000",
                 "OPINFINS 22222222111111000000"):
        receiver.push(line)
    await hass.async_block_till_done()

    assert state(hass, "number.av_20_subwoofer_level").state == "-4.0"
    assert state(hass, "number.av_20_lfe_level").state == "0"
    assert state(hass, "number.av_20_bass").state == "0"
    assert state(hass, "number.av_20_treble").state == "2"
    assert state(hass, "switch.av_20_tone_control").state == "off"
    assert state(hass, "select.av_20_dynamic_range_compression").state == "Off"
    assert state(hass, "binary_sensor.av_20_auto_lip_sync").state == "on"
    assert state(hass, "sensor.av_20_auto_lip_sync_delay").state == "0"
    speakers = state(hass, "sensor.av_20_active_speakers")
    assert speakers.state == "3"
    assert speakers.attributes["channels_available"] == 12
    assert speakers.attributes["pattern"] == "22121111011000011000000000000000"
    assert state(hass, "sensor.av_20_input_channels").state == "8"


async def test_controls_send_commands(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    send = receiver.async_send_telnet_commands
    await call(hass, "number", "set_value", "number.av_20_subwoofer_level", value=-3.5)
    send.assert_awaited_with("PSSWL 465")
    await call(hass, "number", "set_value", "number.av_20_lfe_level", value=-5)
    send.assert_awaited_with("PSLFE 05")
    await call(hass, "number", "set_value", "number.av_20_bass", value=3)
    send.assert_awaited_with("PSTONE CTRL ON", "PSBAS 53")
    await call(hass, "number", "set_value", "number.av_20_treble", value=-2)
    send.assert_awaited_with("PSTONE CTRL ON", "PSTRE 48")
    await call(hass, "switch", "turn_off", "switch.av_20_tone_control")
    send.assert_awaited_with("PSTONE CTRL OFF")
    await call(hass, "select", "select_option", "select.av_20_dynamic_range_compression",
               option="Auto")
    send.assert_awaited_with("PSDRC AUTO")


async def test_channel_trims_created_from_cv_lines(hass: HomeAssistant, receiver: FakeReceiver):
    await setup(hass, receiver, make_entry())
    assert state(hass, "number.av_20_front_left_trim") is None
    for line in ("CVFL 50", "CVFR 505", "CVTTR ON", "CVTTR 50", "CVEND"):
        receiver.push(line)
    await hass.async_block_till_done()
    assert state(hass, "number.av_20_front_left_trim").state == "0.0"
    assert state(hass, "number.av_20_front_right_trim").state == "0.5"
    # The tactile transducer isn't a speaker channel.
    assert not [e for e in hass.states.async_entity_ids("number") if "ttr" in e]

    receiver.push("CVFL 46")
    assert state(hass, "number.av_20_front_left_trim").state == "-4.0"
    await call(hass, "number", "set_value", "number.av_20_front_left_trim", value=1.5)
    receiver.async_send_telnet_commands.assert_awaited_with("CVFL 515")
