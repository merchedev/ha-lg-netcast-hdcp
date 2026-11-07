"""The LG NetCast HDCP integration."""

from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol
from homeassistant.components.media_player import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_HOST,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_KEY,
    CONF_INPUT_SOURCES,
    CONF_IR_STATE_TRACKING,
    CONF_PAIRING_KEY,
    DOMAIN,
    ISSUE_STATE_NOT_TRACKED,
    SERVICE_PROCESS_IR_KEY,
)
from .coordinator import LgNetcastHdcpCoordinator
from .hdcp import LgHdcpClient
from .state import TvStateTracker

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
]

STATE_TRACKING_URL = "https://github.com/merchedev/ha-lg-netcast-hdcp#state-tracking"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class LgNetcastHdcpRuntimeData:
    """Runtime data for a config entry."""

    client: LgHdcpClient
    tracker: TvStateTracker
    coordinator: LgNetcastHdcpCoordinator


type LgNetcastHdcpConfigEntry = ConfigEntry[LgNetcastHdcpRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register integration-level services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_PROCESS_IR_KEY,
        _async_process_ir_key,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
                vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(ATTR_AREA_ID): vol.All(cv.ensure_list, [cv.string]),
                vol.Required(ATTR_KEY): cv.string,
            }
        ),
    )
    return True


async def _async_process_ir_key(call: ServiceCall) -> None:
    """Update the state of one or more televisions from an IR key event."""
    component = call.hass.data.get(DATA_COMPONENT)
    if component is None:
        raise HomeAssistantError("The media player component is not loaded")

    referenced = async_extract_referenced_entity_ids(
        call.hass, TargetSelection(call.data)
    )
    entity_ids = referenced.referenced | referenced.indirectly_referenced
    key = call.data[ATTR_KEY]
    found = False

    for entity_id in entity_ids:
        entity = component.get_entity(entity_id)
        handler = getattr(entity, "async_process_ir_key", None)
        if handler is None:
            continue
        found = True
        await handler(key)

    if not found:
        raise HomeAssistantError("No LG NetCast HDCP media player was targeted")


async def async_setup_entry(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    client = LgHdcpClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PAIRING_KEY],
        async_get_clientsession(hass),
    )
    sources = entry.options.get(CONF_INPUT_SOURCES, {})
    tracker = TvStateTracker(
        sources if isinstance(sources, dict) else {},
        client.profile.direct_input_keys,
    )
    coordinator = LgNetcastHdcpCoordinator(hass, entry, client, tracker)

    entry.runtime_data = LgNetcastHdcpRuntimeData(
        client=client,
        tracker=tracker,
        coordinator=coordinator,
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_sync_state_issue(hass, entry)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_sync_state_issue(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> None:
    """Create or remove the state tracking warning."""
    issue_id = f"{ISSUE_STATE_NOT_TRACKED}_{entry.entry_id}"
    if entry.options.get(CONF_IR_STATE_TRACKING, False) is True:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        data={"entry_id": entry.entry_id},
        is_fixable=True,
        is_persistent=True,
        learn_more_url=STATE_TRACKING_URL,
        severity=ir.IssueSeverity.WARNING,
        translation_key="state_not_tracked",
        translation_placeholders={"name": entry.title},
    )


async def _async_update_listener(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await entry.runtime_data.coordinator.async_shutdown()
    await entry.runtime_data.client.async_close()
    return True


async def async_remove_entry(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> None:
    """Remove the state tracking warning when the entry is deleted."""
    ir.async_delete_issue(
        hass,
        DOMAIN,
        f"{ISSUE_STATE_NOT_TRACKED}_{entry.entry_id}",
    )
