"""HDCP key codes for LG NetCast 2.0 televisions.

These are hexadecimal strings, not the decimal codes used by ROAP (2012+).
Keeping this module free of Home Assistant imports lets the standalone probe
tool share the same key map.
"""

from __future__ import annotations

from typing import Final

HDCP_KEYS: Final[dict[str, str]] = {
    "POWER": "08",
    "ENERGY_SAVING": "95",
    "AV": "30",
    "INPUT": "0B",
    "TV_RADIO": "F0",
    "NUMBER_0": "10",
    "NUMBER_1": "11",
    "NUMBER_2": "12",
    "NUMBER_3": "13",
    "NUMBER_4": "14",
    "NUMBER_5": "15",
    "NUMBER_6": "16",
    "NUMBER_7": "17",
    "NUMBER_8": "18",
    "NUMBER_9": "19",
    "LIST": "53",
    "PREVIOUS_CHANNEL": "1A",
    "VOLUME_UP": "02",
    "VOLUME_DOWN": "03",
    "FAVORITE_CHANNEL": "1E",
    "ASPECT_RATIO": "79",
    "MUTE": "09",
    "CHANNEL_UP": "00",
    "CHANNEL_DOWN": "01",
    "MENU": "43",
    "HOME": "23",
    "WIDGETS": "58",
    "NETCAST": "59",
    "QUICK_MENU": "45",
    "THREE_D": "DC",
    "RIGHT": "06",
    "LEFT": "07",
    "UP": "40",
    "DOWN": "41",
    "OK": "44",
    "BACK": "28",
    "GUIDE": "A9",
    "EXIT": "5B",
    "RED": "72",
    "GREEN": "71",
    "YELLOW": "63",
    "BLUE": "61",
    "TEXT": "20",
    "SUBTITLE": "39",
    "LIVE_TV": "9E",
    "RECORD": "BD",
    "STOP": "B1",
    "PLAY": "B0",
    "PAUSE": "BA",
    "REWIND": "8F",
    "FAST_FORWARD": "8E",
    "SIMPLINK": "7E",
    "INFO": "AA",
    "AUDIO_DESCRIPTION": "91",
    "APPS": "9F",
    "TEXT_OPTION": "21",
}

HDCP_KEY_ALIASES: Final[dict[str, str]] = {
    "3D": "DC",
    "Q_VIEW": "1A",
    "LAST_CHANNEL": "1A",
    "VOL_UP": "02",
    "VOL_DOWN": "03",
    "CH_UP": "00",
    "CH_DOWN": "01",
    "ENTER": "44",
    "SELECT": "44",
    "RETURN": "28",
    "PREV": "28",
    "NETFLIX": "9F",
}
