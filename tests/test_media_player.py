"""Tests for the media player and remote entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.lg_netcast_hdcp.const import (
    CONF_PAIRING_KEY,
    DOMAIN,
)
from custom_components.lg_netcast_hdcp.hdcp import HdcpAuthError, LgHdcpClient
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

HOST = "192.0.2.10"
KEY = "ABC123"


@pytest.fixture
async def setup_integration(hass: HomeAssistant):
    """Set up the integration with a mocked HDCP client."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
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
    """The integration creates a media player and a remote."""
    media_players = hass.states.async_entity_ids("media_player")
    remotes = hass.states.async_entity_ids("remote")

    assert len(media_players) == 1
    assert len(remotes) == 1


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


async def test_play_media_channel(hass: HomeAssistant, setup_integration) -> None:
    """Channel tuning sends digits followed by OK."""
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


async def test_remote_send_command(hass: HomeAssistant, setup_integration) -> None:
    """The remote entity forwards a command list."""
    remote_id = hass.states.async_entity_ids("remote")[0]

    await hass.services.async_call(
        "remote",
        "send_command",
        {"entity_id": remote_id, "command": ["HOME", "DOWN", "OK"]},
        blocking=True,
    )

    LgHdcpClient.async_send_sequence.assert_awaited_with(["HOME", "DOWN", "OK"])


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
            "async_authenticate",
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
    assert hass.states.get(entity_id).state == MediaPlayerState.OFF
    assert start_reauth.called
