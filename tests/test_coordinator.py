"""Tests for the state polling coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from xml.etree import ElementTree

from custom_components.lg_netcast_hdcp.const import DOMAIN
from custom_components.lg_netcast_hdcp.coordinator import (
    LgNetcastHdcpCoordinator,
    TvData,
)
from custom_components.lg_netcast_hdcp.hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    HdcpProtocolError,
)
from custom_components.lg_netcast_hdcp.profiles import DEFAULT_PROFILE
from custom_components.lg_netcast_hdcp.state import TvStateTracker
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

CHANNEL_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<envelope>"
    "<HDCPError>200</HDCPError>"
    "<data>"
    "<type>terrestrial</type>"
    "<major>21</major>"
    "<minor>65535</minor>"
    "<sourceIndex>1</sourceIndex>"
    "<physicalNum>47</physicalNum>"
    "<name>VEO 7</name>"
    "</data>"
    "</envelope>"
)

INVALID_CHANNEL_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<envelope>"
    "<HDCPError>200</HDCPError>"
    "<data>"
    "<type>satellite</type>"
    "<major>16368</major>"
    "<minor>65535</minor>"
    "<sourceIndex>9</sourceIndex>"
    "<physicalNum>65535</physicalNum>"
    "<name></name>"
    "</data>"
    "</envelope>"
)

CONTEXT_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<envelope><HDCPError>200</HDCPError><mode>VolCh</mode></envelope>"
)


def _coordinator(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    tracker: TvStateTracker,
    channel_xml: str,
    context_xml: str | None = CONTEXT_XML,
) -> LgNetcastHdcpCoordinator:
    """Create a coordinator with a fake data endpoint."""
    client = AsyncMock()
    client.profile = DEFAULT_PROFILE

    def query(target: str) -> ElementTree.Element:
        if target == "cur_channel":
            return ElementTree.fromstring(channel_xml)
        if context_xml is None:
            raise HdcpProtocolError("unsupported")
        return ElementTree.fromstring(context_xml)

    client.async_query_data = AsyncMock(side_effect=query)
    return LgNetcastHdcpCoordinator(hass, entry, client, tracker)


async def test_valid_channel_updates_tracker(hass: HomeAssistant) -> None:
    """A valid channel response updates power, channel, and UI mode."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    tracker = TvStateTracker()
    coordinator = _coordinator(hass, entry, tracker, CHANNEL_XML)

    data = await coordinator._async_update_data()

    assert data == TvData(
        power=True,
        channel="21",
        channel_name="VEO 7",
        ui_mode="VolCh",
    )
    assert tracker.power is True
    assert tracker.source is None
    assert tracker.channel == "21"
    assert tracker.channel_name == "VEO 7"
    assert tracker.ui_mode == "VolCh"


async def test_invalid_channel_keeps_known_source(hass: HomeAssistant) -> None:
    """Invalid channel data on an external input keeps the last source."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    tracker = TvStateTracker()
    tracker.set_source("HDMI1")
    coordinator = _coordinator(hass, entry, tracker, INVALID_CHANNEL_XML)

    data = await coordinator._async_update_data()

    assert data.power is True
    assert data.channel is None
    assert tracker.source == "HDMI1"
    assert tracker.channel is None


async def test_ui_mode_failure_keeps_channel(hass: HomeAssistant) -> None:
    """An unsupported context query does not discard channel data."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    tracker = TvStateTracker()
    coordinator = _coordinator(
        hass,
        entry,
        tracker,
        CHANNEL_XML,
        context_xml=None,
    )

    data = await coordinator._async_update_data()

    assert data.channel == "21"
    assert data.ui_mode is None
    assert tracker.channel == "21"


async def test_connection_error_requires_two_failures(
    hass: HomeAssistant,
) -> None:
    """A single connection failure keeps the last known state."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    tracker = TvStateTracker()
    tracker.set_power(True)
    coordinator = _coordinator(hass, entry, tracker, CHANNEL_XML)
    coordinator.data = TvData(power=True, channel="21", channel_name="VEO 7")
    coordinator._client.async_query_data = AsyncMock(
        side_effect=HdcpConnectionError("off")
    )

    first = await coordinator._async_update_data()
    assert first.power is True
    assert tracker.power is True

    second = await coordinator._async_update_data()
    assert second.power is False
    assert tracker.power is False


async def test_auth_error_starts_reauth(hass: HomeAssistant) -> None:
    """A rejected key starts reauthentication and reports the TV as on."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    tracker = TvStateTracker()
    coordinator = _coordinator(hass, entry, tracker, CHANNEL_XML)
    coordinator._client.async_query_data = AsyncMock(
        side_effect=HdcpAuthError("bad key")
    )

    with patch.object(entry, "async_start_reauth") as start_reauth:
        data = await coordinator._async_update_data()

    assert data.power is True
    assert tracker.power is True
    assert start_reauth.called
