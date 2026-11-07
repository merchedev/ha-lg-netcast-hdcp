"""Tests for the state tracking repair flow."""

from __future__ import annotations

from custom_components.lg_netcast_hdcp.const import (
    CONF_IR_STATE_TRACKING,
    CONF_PAIRING_KEY,
    DOMAIN,
)
from custom_components.lg_netcast_hdcp.repairs import async_create_fix_flow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

HOST = "192.0.2.10"
KEY = "ABC123"


async def test_repair_flow_enables_ir_tracking(hass: HomeAssistant) -> None:
    """The repair flow enables IR tracking on the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
        title="LG TV",
    )
    entry.add_to_hass(hass)

    flow = await async_create_fix_flow(
        hass,
        f"state_not_tracked_{entry.entry_id}",
        {"entry_id": entry.entry_id},
    )
    flow.hass = hass
    form = await flow.async_step_init()
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "confirm"
    assert form["description_placeholders"] == {"name": "LG TV"}

    result = await flow.async_step_confirm(user_input={})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_IR_STATE_TRACKING] is True
