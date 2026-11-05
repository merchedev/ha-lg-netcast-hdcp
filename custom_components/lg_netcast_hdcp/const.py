"""Constants for the LG NetCast HDCP integration."""

from __future__ import annotations

from typing import Final

from .keys import HDCP_KEY_ALIASES, HDCP_KEYS

DOMAIN: Final = "lg_netcast_hdcp"
NAME: Final = "LG NetCast HDCP"
MANUFACTURER: Final = "LG"
MODEL: Final = "NetCast HDCP TV"

DEFAULT_PORT: Final = 8080
DEFAULT_TIMEOUT: Final = 5.0

CONF_PAIRING_KEY: Final = "pairing_key"

HDCP_ERROR: Final = "HDCPError"
HDCP_ERROR_DETAIL: Final = "HDCPErrorDetail"
HDCP_SESSION: Final = "session"
HDCP_ERROR_OK: Final = "200"

AUTH_PATH: Final = "auth"
COMMAND_PATH: Final = "dtv_wifirc"

PAIRING_KEY_LENGTH: Final = 6
PAIRING_KEY_PATTERN: Final = r"^[A-Za-z0-9]{6}$"

__all__ = [
    "AUTH_PATH",
    "COMMAND_PATH",
    "CONF_PAIRING_KEY",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "DOMAIN",
    "HDCP_ERROR",
    "HDCP_ERROR_DETAIL",
    "HDCP_ERROR_OK",
    "HDCP_KEYS",
    "HDCP_KEY_ALIASES",
    "HDCP_SESSION",
    "MANUFACTURER",
    "MODEL",
    "NAME",
    "PAIRING_KEY_LENGTH",
    "PAIRING_KEY_PATTERN",
]
