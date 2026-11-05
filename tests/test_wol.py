"""Tests for the Wake-on-LAN helper."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from custom_components.lg_netcast_hdcp.wol import (
    _send_packet,
    async_send_magic_packet,
    build_magic_packet,
    normalize_mac,
)
from homeassistant.exceptions import HomeAssistantError


def test_normalize_mac() -> None:
    """MAC addresses accept common separators."""
    assert normalize_mac("aa:bb:cc:dd:ee:ff") == "AABBCCDDEEFF"
    assert normalize_mac("AA-BB-CC-DD-EE-FF") == "AABBCCDDEEFF"
    assert normalize_mac("AABBCCDDEEFF") == "AABBCCDDEEFF"


def test_normalize_mac_rejects_invalid() -> None:
    """Invalid MAC addresses are rejected."""
    with pytest.raises(ValueError, match="Invalid MAC"):
        normalize_mac("not-a-mac")


def test_build_magic_packet() -> None:
    """The magic packet has the expected structure."""
    packet = build_magic_packet("AA:BB:CC:DD:EE:FF")

    assert len(packet) == 102
    assert packet[:6] == b"\xff" * 6
    assert packet[6:12] == bytes.fromhex("AABBCCDDEEFF")
    assert packet[6:] == bytes.fromhex("AABBCCDDEEFF") * 16


def test_send_packet_uses_broadcast() -> None:
    """The packet is sent to the configured broadcast address."""
    with patch("custom_components.lg_netcast_hdcp.wol.socket.socket") as socket_factory:
        socket_instance = socket_factory.return_value.__enter__.return_value
        _send_packet("AA:BB:CC:DD:EE:FF", "192.168.1.255", 9)

    socket_instance.setsockopt.assert_called_once()
    socket_instance.sendto.assert_called_once()
    assert socket_instance.sendto.call_args.args[1] == ("192.168.1.255", 9)


async def test_async_send_magic_packet(hass) -> None:
    """The async helper runs the sender in the executor."""
    with patch("custom_components.lg_netcast_hdcp.wol._send_packet") as send_packet:
        await async_send_magic_packet(
            hass,
            "AA:BB:CC:DD:EE:FF",
            "192.168.1.255",
            9,
        )

    send_packet.assert_called_once_with(
        "AA:BB:CC:DD:EE:FF",
        "192.168.1.255",
        9,
    )


async def test_async_send_magic_packet_rejects_invalid_mac(hass) -> None:
    """Invalid MAC addresses become a Home Assistant error."""
    with pytest.raises(HomeAssistantError):
        await async_send_magic_packet(hass, "invalid")
