"""Remote key codes for LG NetCast 2.0 televisions.

The television parses the ``HandleKeyInput`` value as a decimal number and
stops at the first non-digit character. The integration's raw-code input is
limited to two-digit decimal strings from ``00`` to ``99``. The named keys
below also include the confirmed three-digit direct-input codes for this
model; use the names, not the raw numbers.

These values were verified on an LG 42LW650S-ZC (NetCast 2.0, firmware
0001.0009). See ``docs/keycodes.md`` for the full test matrix.
"""

from __future__ import annotations

from typing import Final

HDCP_KEYS: Final[dict[str, str]] = {
    "POWER": "08",
    "CHANNEL_UP": "00",
    "CHANNEL_DOWN": "01",
    "VOLUME_UP": "02",
    "VOLUME_DOWN": "03",
    "RIGHT": "06",
    "LEFT": "07",
    "MUTE": "09",
    "Q_MENU": "10",
    "INPUT": "11",
    "TIMER": "14",
    "TV_RADIO": "15",
    "UP": "64",
    "DOWN": "65",
    "HDMI1": "206",
    "HDMI2": "204",
    "HDMI3": "233",
    "HDMI4": "218",
    "NUMBER_0": "16",
    "NUMBER_1": "17",
    "NUMBER_2": "18",
    "NUMBER_3": "19",
    "NUMBER_4": "20",
    "NUMBER_5": "21",
    "NUMBER_6": "22",
    "NUMBER_7": "23",
    "NUMBER_8": "24",
    "NUMBER_9": "25",
    "FAVORITE_CHANNEL": "30",
    "TEXT": "32",
    "TEXT_OPTION": "33",
    "TIME": "38",
    "EXIT": "40",
    "AV_MODE": "48",
    "SUBTITLE_LANGUAGE": "57",
    "HOME": "67",
    "OK": "68",
    "Q_MENU_TOGGLE": "69",
    "PICTURE_MODE": "77",
    "LIST": "83",
    "INFO": "85",
    "PREMIUM": "89",
    "AV1": "90",
    "BLUE": "97",
    "YELLOW": "99",
}

HDCP_KEY_ALIASES: Final[dict[str, str]] = {
    "VOL_UP": "02",
    "VOL_DOWN": "03",
    "CH_UP": "00",
    "CH_DOWN": "01",
    "ENTER": "68",
    "SELECT": "68",
    "HDMI_1": "206",
    "HDMI_2": "204",
    "HDMI_3": "233",
    "HDMI_4": "218",
}

DIRECT_INPUT_KEYS: Final[frozenset[str]] = frozenset(
    {"HDMI1", "HDMI2", "HDMI3", "HDMI4", "AV1"}
)


def direct_input_key(source: str) -> str | None:
    """Return the confirmed direct-input key for a source name, if any."""
    normalized = "".join(str(source).strip().upper().split())
    return normalized if normalized in DIRECT_INPUT_KEYS else None
