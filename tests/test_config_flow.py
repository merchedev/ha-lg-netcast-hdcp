"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.lg_netcast_hdcp.const import (
    CONF_INPUT_SOURCES,
    CONF_IR_STATE_TRACKING,
    CONF_PAIRING_KEY,
    CONF_POWER_OFF_SOURCE,
    CONF_TURN_ON_ACTION,
    CONF_TURN_ON_METHOD,
    CONF_WOL_BROADCAST,
    CONF_WOL_MAC,
    CONF_WOL_PORT,
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
            "async_query_data",
            new=AsyncMock(side_effect=HdcpConnectionError("off")),
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


async def test_options_flow_configures_wol(hass) -> None:
    """Wake-on-LAN options are persisted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TURN_ON_METHOD: "wol",
            CONF_WOL_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_WOL_BROADCAST: "192.168.1.255",
            CONF_WOL_PORT: 9,
            CONF_TURN_ON_ACTION: [],
            CONF_INPUT_SOURCES: {},
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TURN_ON_METHOD] == "wol"
    assert entry.options[CONF_WOL_MAC] == "AA:BB:CC:DD:EE:FF"
    assert entry.options[CONF_WOL_PORT] == 9


async def test_options_flow_requires_mac_for_wol(hass) -> None:
    """WOL without a MAC is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TURN_ON_METHOD: "wol",
            CONF_WOL_MAC: "",
            CONF_WOL_BROADCAST: "255.255.255.255",
            CONF_WOL_PORT: 9,
            CONF_TURN_ON_ACTION: [],
            CONF_INPUT_SOURCES: {},
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_WOL_MAC: "mac_required"}


async def test_options_flow_configures_action_and_sources(hass) -> None:
    """Custom actions and input sources are normalized."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    action = {
        "action": "script.turn_on",
        "target": {"entity_id": "script.lg_tv_ir"},
    }
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TURN_ON_METHOD: "action",
            CONF_WOL_MAC: "",
            CONF_WOL_BROADCAST: "255.255.255.255",
            CONF_WOL_PORT: 9,
            CONF_TURN_ON_ACTION: [action],
            CONF_INPUT_SOURCES: {"hdmi1": ["input", "left", "ok"]},
            CONF_POWER_OFF_SOURCE: "hdmi1",
            CONF_IR_STATE_TRACKING: True,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TURN_ON_ACTION] == [action]
    assert entry.options[CONF_INPUT_SOURCES] == {"hdmi1": ["INPUT", "LEFT", "OK"]}
    assert entry.options[CONF_POWER_OFF_SOURCE] == "hdmi1"
    assert entry.options[CONF_IR_STATE_TRACKING] is True


async def test_options_flow_rejects_unknown_power_off_source(hass) -> None:
    """The source before power off must exist in the input sources."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TURN_ON_METHOD: "none",
            CONF_WOL_MAC: "",
            CONF_WOL_BROADCAST: "255.255.255.255",
            CONF_WOL_PORT: 9,
            CONF_TURN_ON_ACTION: [],
            CONF_INPUT_SOURCES: {"hdmi1": ["INPUT", "LEFT", "OK"]},
            CONF_POWER_OFF_SOURCE: "hdmi2",
            CONF_IR_STATE_TRACKING: False,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_POWER_OFF_SOURCE: "unknown_source"}


async def test_reconfigure_flow_updates_host(hass, mock_client) -> None:
    """The reconfigure flow updates the host and unique ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": HOST, CONF_PAIRING_KEY: KEY},
        unique_id=HOST,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "192.0.2.11"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "192.0.2.11"
    assert entry.unique_id == "192.0.2.11"

    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


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
