"""Repair flows for the LG NetCast HDCP integration."""

from __future__ import annotations

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_IR_STATE_TRACKING, DOMAIN


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create the repair flow for a state tracking issue."""
    entry_id = data.get("entry_id") if data else None
    return EnableIrTrackingRepairFlow(
        entry_id if isinstance(entry_id, str) else None,
        issue_id,
    )


class EnableIrTrackingRepairFlow(RepairsFlow):
    """Enable IR receiver state tracking from a repair."""

    def __init__(self, entry_id: str | None, issue_id: str) -> None:
        """Initialize the repair flow."""
        self._entry_id = entry_id
        self._issue_id = issue_id

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Start the repair flow."""
        return await self.async_step_confirm(user_input)

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Confirm enabling IR receiver state tracking."""
        if self._entry_id is None:
            return self.async_abort(reason="entry_not_found")

        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                entry,
                options={**entry.options, CONF_IR_STATE_TRACKING: True},
            )
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm")
