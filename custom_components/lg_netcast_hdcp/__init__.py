"""The LG NetCast HDCP integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PAIRING_KEY
from .hdcp import LgHdcpClient

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.REMOTE]


@dataclass
class LgNetcastHdcpRuntimeData:
    """Runtime data for a config entry."""

    client: LgHdcpClient


type LgNetcastHdcpConfigEntry = ConfigEntry[LgNetcastHdcpRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    client = LgHdcpClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PAIRING_KEY],
        async_get_clientsession(hass),
    )
    entry.runtime_data = LgNetcastHdcpRuntimeData(client=client)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: LgNetcastHdcpConfigEntry
) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await entry.runtime_data.client.async_close()
    return True
