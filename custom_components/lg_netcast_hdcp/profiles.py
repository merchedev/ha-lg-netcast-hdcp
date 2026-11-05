"""Television profiles for the LG NetCast HDCP integration.

Each profile describes a protocol family and its key map. Supporting another
model should mean adding a profile, not changing the integration logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .keys import HDCP_KEYS


@dataclass(frozen=True, slots=True)
class TvProfile:
    """Capabilities and key map for a television family."""

    key: str
    name: str
    protocol: str
    keys: dict[str, str]


HDCP_2011: Final = TvProfile(
    key="hdcp_2011",
    name="LG NetCast HDCP 2011",
    protocol="hdcp",
    keys=HDCP_KEYS,
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
