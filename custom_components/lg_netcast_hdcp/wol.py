"""Wake-on-LAN helper for the LG NetCast HDCP integration."""

from __future__ import annotations

import ipaddress
import re
import socket

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_WOL_BROADCAST, DEFAULT_WOL_PORT, WOL_MAC_PATTERN

_MAC_CLEAN_RE = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to twelve hexadecimal characters."""
    value = mac.strip()
    if not re.fullmatch(WOL_MAC_PATTERN, value):
        raise ValueError("Invalid MAC address")
    return _MAC_CLEAN_RE.sub("", value).upper()


def build_magic_packet(mac: str) -> bytes:
    """Build a magic packet for a normalized MAC address."""
    mac_bytes = bytes.fromhex(normalize_mac(mac))
    return b"\xff" * 6 + mac_bytes * 16


def _send_packet(mac: str, broadcast: str, port: int) -> None:
    """Send the magic packet from a worker thread."""
    try:
        address = ipaddress.ip_address(broadcast)
    except ValueError as err:
        raise ValueError("Invalid broadcast address") from err

    if address.version != 4:
        raise ValueError("Wake-on-LAN requires an IPv4 broadcast address")

    packet = build_magic_packet(mac)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, port))


async def async_send_magic_packet(
    hass: HomeAssistant,
    mac: str,
    broadcast: str = DEFAULT_WOL_BROADCAST,
    port: int = DEFAULT_WOL_PORT,
) -> None:
    """Send a Wake-on-LAN magic packet."""
    try:
        await hass.async_add_executor_job(
            _send_packet,
            mac,
            broadcast or DEFAULT_WOL_BROADCAST,
            port or DEFAULT_WOL_PORT,
        )
    except (OSError, ValueError) as err:
        raise HomeAssistantError(
            f"Could not send the Wake-on-LAN packet: {err}"
        ) from err
