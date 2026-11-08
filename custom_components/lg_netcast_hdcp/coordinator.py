"""State polling for LG NetCast HDCP televisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from xml.etree import ElementTree

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .hdcp import HdcpAuthError, HdcpConnectionError, HdcpError, LgHdcpClient
from .state import TvStateTracker

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
OFFLINE_CONFIRMATIONS = 2


@dataclass(frozen=True)
class TvData:
    """State read from the television."""

    power: bool
    channel: str | None = None
    channel_name: str | None = None
    program_name: str | None = None
    ui_mode: str | None = None


class LgNetcastHdcpCoordinator(DataUpdateCoordinator[TvData]):
    """Poll the HDCP data endpoint and update the shared tracker."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LgHdcpClient,
        tracker: TvStateTracker,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self._entry = entry
        self._client = client
        self._tracker = tracker
        self._offline_count = 0
        self._channel_names: dict[str, str] = {}
        self._channel_names_loaded = False

    async def _async_update_data(self) -> TvData:
        """Read the current channel and UI mode."""
        try:
            channel_root = await self._client.async_query_data("cur_channel")
        except HdcpAuthError:
            self._entry.async_start_reauth(self.hass)
            self._offline_count = 0
            self._tracker.apply(power=True)
            return self._last_known_data(power=True)
        except HdcpConnectionError:
            self._offline_count += 1
            if self._offline_count < OFFLINE_CONFIRMATIONS and self.data is not None:
                return self.data
            self._tracker.apply(power=False)
            return TvData(power=False)
        except HdcpError as err:
            _LOGGER.debug("Could not query the TV state: %s", err)
            self._offline_count = 0
            self._tracker.apply(power=True)
            return self._last_known_data(power=True)

        self._offline_count = 0
        channel, channel_name, program_name = self._parse_channel(channel_root)
        if channel and not channel_name:
            channel_name = await self._async_lookup_channel_name(channel)
        ui_mode = await self._async_query_ui_mode()

        data = TvData(
            power=True,
            channel=channel,
            channel_name=channel_name,
            program_name=program_name,
            ui_mode=ui_mode,
        )
        if channel is None:
            self._tracker.apply(
                power=True,
                channel=None,
                channel_name=None,
                program_name=None,
                ui_mode=ui_mode,
            )
        else:
            self._tracker.apply(
                power=True,
                source=None,
                channel=channel,
                channel_name=channel_name,
                program_name=program_name,
                ui_mode=ui_mode,
            )
        return data

    async def _async_query_ui_mode(self) -> str | None:
        """Return the current UI mode, tolerating unsupported firmware."""
        try:
            context_root = await self._client.async_query_data("context_ui")
        except HdcpError as err:
            _LOGGER.debug("Could not query the TV UI mode: %s", err)
            return self.data.ui_mode if self.data else None
        return context_root.findtext(".//mode") or None

    def _last_known_data(self, *, power: bool) -> TvData:
        """Return the last known state with an updated power value."""
        if self.data is None:
            return TvData(power=power)
        return TvData(
            power=power,
            channel=self.data.channel,
            channel_name=self.data.channel_name,
            program_name=self.data.program_name,
            ui_mode=self.data.ui_mode,
        )

    async def _async_lookup_channel_name(self, channel: str) -> str | None:
        """Look up a channel name when the current-channel response has none."""
        if not self._channel_names_loaded:
            await self._async_load_channel_names()
        return self._channel_names.get(channel)

    async def _async_load_channel_names(self) -> None:
        """Load the channel list once and cache channel names."""
        self._channel_names_loaded = True
        try:
            root = await self._client.async_query_data("channel_list")
        except HdcpError as err:
            _LOGGER.debug("Could not load the TV channel list: %s", err)
            return

        profile = self._client.profile
        names: dict[str, str] = {}
        for data in root.findall(".//data"):
            major = self._find_text(data, "major", "displayMajor")
            if not major or major == profile.invalid_channel_major:
                continue

            name = self._find_text(data, "chname", "name")
            if not name:
                continue

            names[major] = name
            minor = self._find_text(data, "minor", "displayMinor")
            if minor and minor not in (
                profile.no_subchannel,
                profile.invalid_physical_num,
                "65520",
            ):
                names[f"{major}.{minor}"] = name

        self._channel_names = names
        _LOGGER.debug("Loaded %d channel names from the TV", len(names))

    @staticmethod
    def _find_text(data: ElementTree.Element, *names: str) -> str | None:
        """Return the first non-empty child text matching a tag name."""
        wanted = {name.casefold() for name in names}
        for child in data:
            tag = child.tag.rsplit("}", 1)[-1].casefold()
            if tag in wanted:
                text = (child.text or "").strip()
                if text:
                    return text
        return None

    def _parse_channel(
        self,
        root: ElementTree.Element,
    ) -> tuple[str | None, str | None, str | None]:
        """Parse the current-channel response."""
        data = root.find(".//data")
        if data is None:
            return None, None, None

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Channel data: %s",
                ElementTree.tostring(data, encoding="unicode"),
            )

        profile = self._client.profile
        major = self._find_text(data, "major", "displayMajor")
        minor = self._find_text(data, "minor", "displayMinor")
        physical_num = self._find_text(data, "physicalNum")
        channel_name = self._find_text(
            data,
            "name",
            "chname",
            "inputSourceName",
            "labelName",
        )
        program_name = self._find_text(
            data,
            "progName",
            "programName",
            "program",
        )

        if (
            not major
            or major == profile.invalid_channel_major
            or physical_num == profile.invalid_physical_num
        ):
            return None, None, None

        if minor and minor != profile.no_subchannel:
            return f"{major}.{minor}", channel_name, program_name
        return major, channel_name, program_name
