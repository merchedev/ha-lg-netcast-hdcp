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
CONF_TURN_ON_METHOD: Final = "turn_on_method"
CONF_WOL_MAC: Final = "wol_mac"
CONF_WOL_BROADCAST: Final = "wol_broadcast"
CONF_WOL_PORT: Final = "wol_port"
CONF_TURN_ON_ACTION: Final = "turn_on_action"
CONF_INPUT_SOURCES: Final = "input_sources"
CONF_POWER_OFF_SOURCE: Final = "power_off_source"
CONF_IR_STATE_TRACKING: Final = "ir_state_tracking"

TURN_ON_METHOD_NONE: Final = "none"
TURN_ON_METHOD_WOL: Final = "wol"
TURN_ON_METHOD_ACTION: Final = "action"
TURN_ON_METHOD_BOTH: Final = "both"
TURN_ON_METHODS: Final = (
    TURN_ON_METHOD_NONE,
    TURN_ON_METHOD_WOL,
    TURN_ON_METHOD_ACTION,
    TURN_ON_METHOD_BOTH,
)
DEFAULT_TURN_ON_METHOD: Final = TURN_ON_METHOD_NONE
DEFAULT_WOL_BROADCAST: Final = "255.255.255.255"
DEFAULT_WOL_PORT: Final = 9
WOL_MAC_PATTERN: Final = r"^[0-9A-Fa-f]{2}([:-]?[0-9A-Fa-f]{2}){5}$"
RAW_KEY_PATTERN: Final = r"^\d{2}$"

POWER_OFF_SOURCE_DELAY: Final = 2.0

SERVICE_PROCESS_IR_KEY: Final = "process_ir_key"
ATTR_KEY: Final = "key"
ISSUE_STATE_NOT_TRACKED: Final = "state_not_tracked"

HDCP_ERROR: Final = "HDCPError"
HDCP_ERROR_DETAIL: Final = "HDCPErrorDetail"
HDCP_SESSION: Final = "session"
HDCP_ERROR_OK: Final = "200"

AUTH_PATH: Final = "auth"
COMMAND_PATH: Final = "dtv_wifirc"
DATA_PATH: Final = "data"

PAIRING_KEY_LENGTH: Final = 6
PAIRING_KEY_PATTERN: Final = r"^[A-Za-z0-9]{6}$"

__all__ = [
    "ATTR_KEY",
    "AUTH_PATH",
    "COMMAND_PATH",
    "CONF_INPUT_SOURCES",
    "CONF_IR_STATE_TRACKING",
    "CONF_PAIRING_KEY",
    "CONF_POWER_OFF_SOURCE",
    "CONF_TURN_ON_ACTION",
    "CONF_TURN_ON_METHOD",
    "CONF_WOL_BROADCAST",
    "CONF_WOL_MAC",
    "CONF_WOL_PORT",
    "DATA_PATH",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_TURN_ON_METHOD",
    "DEFAULT_WOL_BROADCAST",
    "DEFAULT_WOL_PORT",
    "DOMAIN",
    "HDCP_ERROR",
    "HDCP_ERROR_DETAIL",
    "HDCP_ERROR_OK",
    "HDCP_KEYS",
    "HDCP_KEY_ALIASES",
    "HDCP_SESSION",
    "ISSUE_STATE_NOT_TRACKED",
    "MANUFACTURER",
    "MODEL",
    "NAME",
    "PAIRING_KEY_LENGTH",
    "PAIRING_KEY_PATTERN",
    "POWER_OFF_SOURCE_DELAY",
    "RAW_KEY_PATTERN",
    "SERVICE_PROCESS_IR_KEY",
    "TURN_ON_METHODS",
    "TURN_ON_METHOD_ACTION",
    "TURN_ON_METHOD_BOTH",
    "TURN_ON_METHOD_NONE",
    "TURN_ON_METHOD_WOL",
    "WOL_MAC_PATTERN",
]
