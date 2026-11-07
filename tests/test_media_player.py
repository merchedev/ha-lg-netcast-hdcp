"""Tests for the media player and remote entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, call, patch
from xml.etree import ElementTree

import pytest
from custom_components.lg_netcast_hdcp.const import (
    CONF_INPUT_SOURCES,
    CONF_IR_STATE_TRACKING,
    CONF_PAIRING_KEY,
    CONF_POWER_OFF_SOURCE,
    CONF_TURN_ON_ACTION,
    CONF_TURN_ON_METHOD,
    CONF_WOL_BROADCAST,
    CONF_WOL_MAC,
    CONF_WOL_PORT,
    DOMAIN,
    POWER_OFF_SOURCE_DELAY,
)
from custom_components.lg_netcast_hdcp.hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    LgHdcpClient,
)
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

HOST = "192.0.2.10"
KEY = "ABC123"

CHANNEL_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<envelope>"
    "<HDCPError>200</HDCPError>"
    "<HDCPErrorDetail>OK</HDCPErrorDetail>"
    "<data>"
    "<type>terrestrial</type>"
    "<major>21</major>"
    "<minor>65535</minor>"
    "<sourceIndex>1</sourceIndex>"
    "<physicalNum>47</physicalNum>"
    "<name>VEO 7</name>"
    "</data>"
    "</envelope>"
)

CONTEXT_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<envelope>"
    "<HDCPError>200</HDCPError>"
    "<HDCPErrorDetail>OK</HDCPErrorDetail>"
    "<mode>VolCh</mode>"
    "</envelope>"
)


def _query_data(target: str) -> ElementTree.Element:
    """Return a fake data response for the requested target."""
    if target == "cur_channel":
        return ElementTree.fromstring(CHANNEL_XML)
    return ElementTree.fromstring(CONTEXT_XML)


@pytest.fixture
async def setup_integration(hass: HomeAssistant, request):
    """Set up the integration with a mocked HDCP client."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        options=getattr(request, "param", {}),
        unique_id=HOST,
        title="LG TV",
    )
    entry.add_to_hass(hass)

    with (
        patch.object(
            LgHdcpClient,
            "async_authenticate",
            new=AsyncMock(return_value="123456789"),
        ),
        patch.object(
            LgHdcpClient,
            "async_query_data",
            new=AsyncMock(side_effect=_query_data),
        ),
        patch.object(
            LgHdcpClient,
            "async_send_key",
            new=AsyncMock(),
        ),
        patch.object(
            LgHdcpClient,
            "async_send_sequence",
            new=AsyncMock(),
        ),
        patch.object(
            LgHdcpClient,
            "async_close",
            new=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


async def test_entities_created(hass: HomeAssistant, setup_integration) -> None:
    """The integration creates a media player, remote, and buttons."""
    media_players = hass.states.async_entity_ids("media_player")
    remotes = hass.states.async_entity_ids("remote")
    buttons = hass.states.async_entity_ids("button")

    assert len(media_players) == 1
    assert len(remotes) == 1
    assert len(buttons) == 27


async def test_channel_state_from_data_endpoint(
    hass: HomeAssistant, setup_integration
) -> None:
    """The channel and UI mode come from the data endpoint."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    state = hass.states.get(entity_id)

    assert state.state == STATE_ON
    assert state.attributes["media_channel"] == "21"
    assert state.attributes["media_title"] == "VEO 7"
    assert state.attributes["ui_mode"] == "VolCh"


async def test_turn_off_sends_power(hass: HomeAssistant, setup_integration) -> None:
    """Turning off sends the POWER key."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    LgHdcpClient.async_send_key.assert_awaited_with("POWER")
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_volume_and_mute(hass: HomeAssistant, setup_integration) -> None:
    """Volume and mute use the correct keys."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "volume_up",
        {"entity_id": entity_id},
        blocking=True,
    )
    LgHdcpClient.async_send_key.assert_awaited_with("VOLUME_UP")

    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {"entity_id": entity_id, "is_volume_muted": True},
        blocking=True,
    )
    LgHdcpClient.async_send_key.assert_awaited_with("MUTE")
    assert hass.states.get(entity_id).attributes["is_volume_muted"] is True


async def test_play_media_channel(hass: HomeAssistant, setup_integration) -> None:
    """Channel tuning sends digits followed by OK and updates the channel."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": entity_id,
            "media_content_id": "12",
            "media_content_type": "channel",
        },
        blocking=True,
    )

    LgHdcpClient.async_send_sequence.assert_awaited_with(["NUMBER_1", "NUMBER_2", "OK"])
    assert hass.states.get(entity_id).attributes["media_channel"] == "12"


async def test_remote_send_command(hass: HomeAssistant, setup_integration) -> None:
    """The remote entity forwards a command list."""
    remote_id = hass.states.async_entity_ids("remote")[0]

    await hass.services.async_call(
        "remote",
        "send_command",
        {"entity_id": remote_id, "command": ["HOME", "LEFT", "OK"]},
        blocking=True,
    )

    LgHdcpClient.async_send_sequence.assert_awaited_with(["HOME", "LEFT", "OK"])


async def test_no_turn_on_feature_without_method(
    hass: HomeAssistant, setup_integration
) -> None:
    """The turn-on feature is hidden until a method is configured."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    features = hass.states.get(entity_id).attributes["supported_features"]

    assert not features & MediaPlayerEntityFeature.TURN_ON


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_TURN_ON_METHOD: "wol",
            CONF_WOL_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_WOL_BROADCAST: "192.168.1.255",
            CONF_WOL_PORT: 9,
        }
    ],
    indirect=True,
)
async def test_turn_on_with_wol(hass: HomeAssistant, setup_integration) -> None:
    """Wake-on-LAN sends the configured magic packet."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    with patch(
        "custom_components.lg_netcast_hdcp.media_player.async_send_magic_packet",
        new=AsyncMock(),
    ) as send_magic_packet:
        await hass.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True,
        )

    send_magic_packet.assert_awaited_once_with(
        hass,
        "AA:BB:CC:DD:EE:FF",
        "192.168.1.255",
        9,
    )
    assert hass.states.get(entity_id).state == STATE_ON


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_TURN_ON_METHOD: "action",
            CONF_TURN_ON_ACTION: [
                {
                    "action": "script.turn_on",
                    "target": {"entity_id": "script.lg_tv_ir"},
                }
            ],
        }
    ],
    indirect=True,
)
async def test_turn_on_with_custom_action(
    hass: HomeAssistant, setup_integration
) -> None:
    """A custom action is executed when configured."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    with patch(
        "custom_components.lg_netcast_hdcp.media_player.async_call_from_config",
        new=AsyncMock(),
    ) as call_action:
        await hass.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True,
        )

    call_action.assert_awaited_once()
    assert hass.states.get(entity_id).state == STATE_ON


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_TURN_ON_METHOD: "action",
            CONF_TURN_ON_ACTION: [
                {
                    "action": "script.turn_on",
                    "target": {"entity_id": "script.lg_tv_ir"},
                }
            ],
        }
    ],
    indirect=True,
)
async def test_turn_on_with_failing_action_keeps_state(
    hass: HomeAssistant, setup_integration
) -> None:
    """A failed power-on action leaves the current state untouched."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    assert hass.states.get(entity_id).state == STATE_ON

    with (
        patch(
            "custom_components.lg_netcast_hdcp.media_player.async_call_from_config",
            new=AsyncMock(side_effect=HomeAssistantError("IR action failed")),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True,
        )

    assert hass.states.get(entity_id).state == STATE_ON


async def test_failed_command_marks_state_unknown(
    hass: HomeAssistant, setup_integration
) -> None:
    """A command that cannot reach the TV leaves the state unknown."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    assert hass.states.get(entity_id).state == STATE_ON

    with patch.object(
        LgHdcpClient,
        "async_send_key",
        new=AsyncMock(side_effect=HdcpConnectionError("TV is unreachable")),
    ):
        await hass.services.async_call(
            "media_player",
            "volume_up",
            {"entity_id": entity_id},
            blocking=True,
        )

    assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_failed_turn_off_does_not_report_off(
    hass: HomeAssistant, setup_integration
) -> None:
    """A failed power-off command does not report the TV as off."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    assert hass.states.get(entity_id).state == STATE_ON

    with patch.object(
        LgHdcpClient,
        "async_send_key",
        new=AsyncMock(side_effect=HdcpConnectionError("TV is unreachable")),
    ):
        await hass.services.async_call(
            "media_player",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )

    assert hass.states.get(entity_id).state == STATE_UNKNOWN


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "HDMI1": ["INPUT", "LEFT", "OK"],
                "HDMI2": ["INPUT", "LEFT", "LEFT", "OK"],
            }
        }
    ],
    indirect=True,
)
async def test_select_source_uses_direct_key(
    hass: HomeAssistant, setup_integration
) -> None:
    """A named HDMI source uses its confirmed direct key."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": entity_id, "source": "HDMI2"},
        blocking=True,
    )

    LgHdcpClient.async_send_key.assert_awaited_with("HDMI2")
    LgHdcpClient.async_send_sequence.assert_not_awaited()
    assert hass.states.get(entity_id).attributes["source"] == "HDMI2"


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "Apple TV": ["INPUT", "LEFT", "OK"],
            }
        }
    ],
    indirect=True,
)
async def test_select_source_uses_sequence_for_custom_name(
    hass: HomeAssistant, setup_integration
) -> None:
    """A source without a direct key uses its configured sequence."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": entity_id, "source": "Apple TV"},
        blocking=True,
    )

    LgHdcpClient.async_send_sequence.assert_awaited_with(["INPUT", "LEFT", "OK"])
    assert hass.states.get(entity_id).attributes["source"] == "Apple TV"


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "HDMI1": ["INPUT", "LEFT", "OK"],
            },
            CONF_POWER_OFF_SOURCE: "HDMI1",
        }
    ],
    indirect=True,
)
async def test_turn_off_selects_direct_power_off_source(
    hass: HomeAssistant, setup_integration
) -> None:
    """The CEC source is selected with a direct key before power off."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    with patch(
        "custom_components.lg_netcast_hdcp.media_player.asyncio.sleep",
        new=AsyncMock(),
    ) as sleep:
        await hass.services.async_call(
            "media_player",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )

    LgHdcpClient.async_send_key.assert_has_awaits([call("HDMI1"), call("POWER")])
    sleep.assert_awaited_once_with(POWER_OFF_SOURCE_DELAY)
    assert setup_integration.runtime_data.tracker.source == "HDMI1"
    assert hass.states.get(entity_id).state == STATE_OFF


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "HDMI1": ["INPUT", "LEFT", "OK"],
            },
            CONF_POWER_OFF_SOURCE: "HDMI2",
        }
    ],
    indirect=True,
)
async def test_turn_off_ignores_unknown_power_off_source(
    hass: HomeAssistant, setup_integration
) -> None:
    """An unknown power-off source is skipped before power off."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    LgHdcpClient.async_send_key.assert_has_awaits([call("POWER")])
    assert hass.states.get(entity_id).state == STATE_OFF


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "Apple TV": ["INPUT", "LEFT", "OK"],
            },
            CONF_POWER_OFF_SOURCE: "Apple TV",
        }
    ],
    indirect=True,
)
async def test_turn_off_selects_sequence_power_off_source(
    hass: HomeAssistant, setup_integration
) -> None:
    """A source without a direct key is selected with its sequence."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    with patch(
        "custom_components.lg_netcast_hdcp.media_player.asyncio.sleep",
        new=AsyncMock(),
    ) as sleep:
        await hass.services.async_call(
            "media_player",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )

    LgHdcpClient.async_send_sequence.assert_awaited_with(["INPUT", "LEFT", "OK"])
    LgHdcpClient.async_send_key.assert_awaited_with("POWER")
    sleep.assert_awaited_once_with(POWER_OFF_SOURCE_DELAY)
    assert setup_integration.runtime_data.tracker.source == "Apple TV"
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_button_press_sends_key(hass: HomeAssistant, setup_integration) -> None:
    """A button entity sends its configured key."""
    button_id = next(
        entity_id
        for entity_id in hass.states.async_entity_ids("button")
        if hass.states.get(entity_id)
        .attributes.get("friendly_name", "")
        .endswith("Home")
    )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": button_id},
        blocking=True,
    )

    LgHdcpClient.async_send_key.assert_awaited_with("HOME")


async def test_up_down_buttons_send_keys(
    hass: HomeAssistant, setup_integration
) -> None:
    """Up and Down buttons use the confirmed key codes."""
    buttons = hass.states.async_entity_ids("button")
    up_id = next(
        entity_id
        for entity_id in buttons
        if hass.states.get(entity_id)
        .attributes.get("friendly_name", "")
        .endswith(" Up")
    )
    down_id = next(
        entity_id
        for entity_id in buttons
        if hass.states.get(entity_id)
        .attributes.get("friendly_name", "")
        .endswith(" Down")
    )

    await hass.services.async_call(
        "button", "press", {"entity_id": up_id}, blocking=True
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": down_id}, blocking=True
    )

    LgHdcpClient.async_send_key.assert_has_awaits([call("UP"), call("DOWN")])


async def test_hdmi_buttons_send_direct_keys(
    hass: HomeAssistant, setup_integration
) -> None:
    """HDMI buttons send the confirmed direct-input keys."""
    buttons = hass.states.async_entity_ids("button")

    for name in ("HDMI1", "HDMI2", "HDMI3", "HDMI4"):
        button_id = next(
            entity_id
            for entity_id in buttons
            if hass.states.get(entity_id)
            .attributes.get("friendly_name", "")
            .endswith(f" {name}")
        )
        await hass.services.async_call(
            "button", "press", {"entity_id": button_id}, blocking=True
        )

    LgHdcpClient.async_send_key.assert_has_awaits(
        [call("HDMI1"), call("HDMI2"), call("HDMI3"), call("HDMI4")]
    )
    assert setup_integration.runtime_data.tracker.source == "HDMI4"


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "HDMI1": ["INPUT", "LEFT", "OK"],
            }
        }
    ],
    indirect=True,
)
async def test_media_title_falls_back_to_source(
    hass: HomeAssistant, setup_integration
) -> None:
    """The media title shows the input when no channel is known."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": entity_id, "source": "HDMI1"},
        blocking=True,
    )

    state = hass.states.get(entity_id)
    assert state.attributes["source"] == "HDMI1"
    assert state.attributes["media_title"] == "HDMI1"
    assert "media_channel" not in state.attributes


async def test_process_ir_key_service_power(
    hass: HomeAssistant, setup_integration
) -> None:
    """The IR key service toggles power without sending a command."""
    entity_id = hass.states.async_entity_ids("media_player")[0]
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        DOMAIN,
        "process_ir_key",
        {"entity_id": entity_id, "key": "POWER"},
        blocking=True,
    )

    assert hass.states.get(entity_id).state == STATE_OFF
    LgHdcpClient.async_send_key.assert_not_awaited()


@pytest.mark.parametrize(
    "setup_integration",
    [
        {
            CONF_INPUT_SOURCES: {
                "HDMI1": ["INPUT", "LEFT", "OK"],
            }
        }
    ],
    indirect=True,
)
async def test_process_ir_key_service_input_sequence(
    hass: HomeAssistant, setup_integration
) -> None:
    """The IR key service tracks a configured input sequence."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    for key in ("INPUT", "LEFT", "OK"):
        await hass.services.async_call(
            DOMAIN,
            "process_ir_key",
            {"entity_id": entity_id, "key": key},
            blocking=True,
        )

    assert hass.states.get(entity_id).attributes["source"] == "HDMI1"


async def test_process_ir_key_service_rejects_unknown_key(
    hass: HomeAssistant, setup_integration
) -> None:
    """An unsupported IR key raises a service error."""
    entity_id = hass.states.async_entity_ids("media_player")[0]

    with pytest.raises(HomeAssistantError, match="Unsupported IR key"):
        await hass.services.async_call(
            DOMAIN,
            "process_ir_key",
            {"entity_id": entity_id, "key": "NOT_A_KEY"},
            blocking=True,
        )


async def test_state_warning_issue_created(
    hass: HomeAssistant, setup_integration
) -> None:
    """The state limitation warning is created when IR tracking is off."""
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN,
        f"state_not_tracked_{setup_integration.entry_id}",
    )
    assert issue is not None


@pytest.mark.parametrize(
    "setup_integration",
    [{CONF_IR_STATE_TRACKING: True}],
    indirect=True,
)
async def test_state_warning_issue_removed_with_ir_tracking(
    hass: HomeAssistant, setup_integration
) -> None:
    """Enabling IR tracking suppresses the state limitation warning."""
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN,
        f"state_not_tracked_{setup_integration.entry_id}",
    )
    assert issue is None


async def test_setup_handles_auth_failure(hass: HomeAssistant) -> None:
    """A rejected pairing key does not crash setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
        title="LG TV",
    )
    entry.add_to_hass(hass)

    with (
        patch.object(entry, "async_start_reauth") as start_reauth,
        patch.object(
            LgHdcpClient,
            "async_query_data",
            new=AsyncMock(side_effect=HdcpAuthError("bad key")),
        ),
        patch.object(
            LgHdcpClient,
            "async_send_key",
            new=AsyncMock(),
        ),
        patch.object(
            LgHdcpClient,
            "async_send_sequence",
            new=AsyncMock(),
        ),
        patch.object(
            LgHdcpClient,
            "async_close",
            new=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_id = hass.states.async_entity_ids("media_player")[0]
    assert hass.states.get(entity_id).state == STATE_ON
    assert start_reauth.called
