"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.lg_netcast_hdcp.const import (
    CONF_PAIRING_KEY,
    DOMAIN,
)
from custom_components.lg_netcast_hdcp.hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    LgHdcpClient,
)
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

HOST = "192.0.2.10"
KEY = "ABC123"


@pytest.fixture
def mock_client():
    """Patch the client methods used by the config flow."""
    with (
        patch.object(
            LgHdcpClient,
            "async_request_pairing_key",
            new=AsyncMock(),
        ),
        patch.object(
            LgHdcpClient,
            "async_authenticate",
            new=AsyncMock(return_value="123456789"),
        ),
        patch.object(
            LgHdcpClient,
            "async_close",
            new=AsyncMock(),
        ),
    ):
        yield


async def test_user_flow_creates_entry(hass, mock_client) -> None:
    """The user flow creates an entry after a successful pairing."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": HOST},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PAIRING_KEY: KEY},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_PAIRING_KEY: KEY, "host": HOST}
    assert result["title"] == f"LG TV ({HOST})"


async def test_user_flow_rejects_invalid_host(hass, mock_client) -> None:
    """An invalid host is reported on the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "not a host"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}


async def test_user_flow_rejects_invalid_key(hass, mock_client) -> None:
    """The pairing key must be six alphanumeric characters."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": HOST},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PAIRING_KEY: "123"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_PAIRING_KEY: "invalid_key"}


async def test_user_flow_rejects_invalid_auth(hass, mock_client) -> None:
    """A rejected pairing key is reported on the form."""
    with patch.object(
        LgHdcpClient,
        "async_authenticate",
        new=AsyncMock(side_effect=HdcpAuthError("bad key")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": HOST},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PAIRING_KEY: KEY},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_reports_connection_error(hass, mock_client) -> None:
    """A connection failure is reported on the pairing form."""
    with patch.object(
        LgHdcpClient,
        "async_request_pairing_key",
        new=AsyncMock(side_effect=HdcpConnectionError("off")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": HOST},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_updates_key(hass, mock_client) -> None:
    """The reauth flow replaces the stored pairing key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: "OLDKEY"},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PAIRING_KEY: KEY},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PAIRING_KEY] == KEY

    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
