"""Remote entity for LG NetCast HDCP televisions."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LgNetcastHdcpConfigEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .hdcp import HdcpAuthError, HdcpError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LgNetcastHdcpConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the remote entity."""
    async_add_entities([LgNetcastHdcpRemote(entry)])


class LgNetcastHdcpRemote(RemoteEntity):
    """Send raw or named keys to the television."""

    _attr_has_entity_name = True
    _attr_name = "Remote"
    _attr_should_poll = False
    _attr_supported_features = RemoteEntityFeature(0)

    def __init__(self, entry: LgNetcastHdcpConfigEntry) -> None:
        """Initialize the remote."""
        self._entry = entry
        self._client = entry.runtime_data.client
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_remote"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
        )

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        """Send one or more keys."""
        commands = list(command)
        tracker = self._entry.runtime_data.tracker
        try:
            await self._client.async_send_sequence(commands)
        except HdcpAuthError as err:
            tracker.set_power(None)
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "The TV rejected the pairing key; reauthentication is required"
            ) from err
        except HdcpError as err:
            tracker.set_power(None)
            raise HomeAssistantError(f"Could not send the command: {err}") from err
        else:
            for key in commands:
                tracker.process_sent_key(key)
