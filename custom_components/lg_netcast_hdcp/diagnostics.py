"""Diagnostics support for the LG NetCast HDCP integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_PAIRING_KEY
from .hdcp import LgHdcpClient

TO_REDACT = {CONF_PAIRING_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client: LgHdcpClient | None = getattr(
        getattr(entry, "runtime_data", None), "client", None
    )

    return {
        "entry": async_redact_data(
            {
                "host": entry.data.get(CONF_HOST),
                "pairing_key": entry.data.get(CONF_PAIRING_KEY),
            },
            TO_REDACT,
        ),
        "client": {
            "session_valid": client.session_valid if client else False,
            "last_error": client.last_error if client else None,
        },
    }
