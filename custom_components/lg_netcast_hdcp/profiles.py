"""Television profiles for the LG NetCast HDCP integration.

Each profile describes a protocol family and its key map. Supporting another
model should mean adding a profile, not changing the integration logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .keys import HDCP_KEYS

DIRECT_INPUT_KEYS: Final[dict[str, str]] = {
    "HDMI1": "HDMI1",
    "HDMI2": "HDMI2",
    "HDMI3": "HDMI3",
    "HDMI4": "HDMI4",
    "AV1": "AV1",
}


def normalize_source_name(value: str) -> str:
    """Normalize a source name for comparison."""
    return "".join(str(value).strip().upper().replace("_", " ").split())


@dataclass(frozen=True, slots=True)
class TvProfile:
    """Capabilities and key map for a television family."""

    key: str
    name: str
    protocol: str
    keys: dict[str, str]
    direct_input_keys: dict[str, str]
    invalid_channel_major: str
    invalid_physical_num: str
    no_subchannel: str

    def direct_input_source(self, source: str) -> str | None:
        """Return the canonical source name for a direct input."""
        normalized = normalize_source_name(source)
        for name in self.direct_input_keys:
            if normalize_source_name(name) == normalized:
                return name
        return None

    def direct_input_key(self, source: str) -> str | None:
        """Return the named key for a direct input source, if any."""
        name = self.direct_input_source(source)
        return self.direct_input_keys[name] if name is not None else None


HDCP_2011: Final = TvProfile(
    key="hdcp_2011",
    name="LG NetCast HDCP 2011",
    protocol="hdcp",
    keys=HDCP_KEYS,
    direct_input_keys=DIRECT_INPUT_KEYS,
    invalid_channel_major="16368",
    invalid_physical_num="65535",
    no_subchannel="65535",
)

DEFAULT_PROFILE: Final = HDCP_2011

PROFILES: Final[dict[str, TvProfile]] = {
    profile.key: profile for profile in (HDCP_2011,)
}


def get_profile(key: str | None) -> TvProfile:
    """Return a profile by key, falling back to the default."""
    if key and key in PROFILES:
        return PROFILES[key]
    return DEFAULT_PROFILE
