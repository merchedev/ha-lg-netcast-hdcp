"""Tests for diagnostics redaction."""

from __future__ import annotations

from custom_components.lg_netcast_hdcp.const import (
    CONF_PAIRING_KEY,
    DOMAIN,
)
from custom_components.lg_netcast_hdcp.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

HOST = "192.0.2.10"
KEY = "ABC123"


async def test_diagnostics_redacts_pairing_key(hass: HomeAssistant) -> None:
    """The pairing key must never appear in diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["host"] == HOST
    assert diagnostics["entry"][CONF_PAIRING_KEY] == "**REDACTED**"
    assert KEY not in str(diagnostics)
