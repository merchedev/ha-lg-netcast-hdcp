"""Config flow for the LG NetCast HDCP integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.network import is_host_valid

from .const import (
    CONF_PAIRING_KEY,
    DOMAIN,
    PAIRING_KEY_LENGTH,
    PAIRING_KEY_PATTERN,
)
from .hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    HdcpError,
    HdcpProtocolError,
    LgHdcpClient,
)
from .options_flow import LgNetcastHdcpOptionsFlow

_LOGGER = logging.getLogger(__name__)

PAIRING_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PAIRING_KEY): cv.string,
    }
)


class LgNetcastHdcpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for an LG NetCast HDCP TV."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._pairing_requested = False
        self._entry = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if not is_host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                self._host = host
                await self.async_set_unique_id(host.lower())
                self._abort_if_unique_id_configured()
                return await self.async_step_pair()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): cv.string}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return LgNetcastHdcpOptionsFlow()

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the pairing key and validate it."""
        assert self._host is not None
        errors: dict[str, str] = {}

        if not self._pairing_requested:
            error = await self._async_request_pairing_key(self._host)
            if error:
                errors["base"] = error
            else:
                self._pairing_requested = True

        if user_input is not None:
            pairing_key = user_input[CONF_PAIRING_KEY].strip().upper()
            if not re.fullmatch(PAIRING_KEY_PATTERN, pairing_key):
                errors[CONF_PAIRING_KEY] = "invalid_key"
            else:
                error = await self._async_validate_key(self._host, pairing_key)
                if error:
                    errors["base"] = error
                else:
                    return self.async_create_entry(
                        title=f"LG TV ({self._host})",
                        data={
                            CONF_HOST: self._host,
                            CONF_PAIRING_KEY: pairing_key,
                        },
                    )

        return self.async_show_form(
            step_id="pair",
            data_schema=PAIRING_KEY_SCHEMA,
            errors=errors,
            description_placeholders={
                "host": self._host,
                "length": str(PAIRING_KEY_LENGTH),
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start reauthentication for an existing entry."""
        self._entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if self._entry is None:
            return self.async_abort(reason="entry_not_found")

        self._host = self._entry.data[CONF_HOST]
        self._pairing_requested = False
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new pairing key."""
        assert self._entry is not None
        assert self._host is not None
        errors: dict[str, str] = {}

        if not self._pairing_requested:
            error = await self._async_request_pairing_key(self._host)
            if error:
                errors["base"] = error
            else:
                self._pairing_requested = True

        if user_input is not None:
            pairing_key = user_input[CONF_PAIRING_KEY].strip().upper()
            if not re.fullmatch(PAIRING_KEY_PATTERN, pairing_key):
                errors[CONF_PAIRING_KEY] = "invalid_key"
            else:
                error = await self._async_validate_key(self._host, pairing_key)
                if error:
                    errors["base"] = error
                else:
                    return self.async_update_reload_and_abort(
                        self._entry,
                        data_updates={CONF_PAIRING_KEY: pairing_key},
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PAIRING_KEY_SCHEMA,
            errors=errors,
            description_placeholders={
                "host": self._host,
                "length": str(PAIRING_KEY_LENGTH),
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow the host to be changed."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        errors: dict[str, str] = {}
        host = entry.data[CONF_HOST]

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if not is_host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                existing = self.hass.config_entries.async_entry_for_domain_unique_id(
                    DOMAIN, host.lower()
                )
                if existing is not None and existing.entry_id != entry.entry_id:
                    return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=host.lower(),
                    title=f"LG TV ({host})",
                    data_updates={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=host): cv.string}),
            errors=errors,
        )

    async def _async_request_pairing_key(self, host: str) -> str | None:
        """Ask the TV to show a pairing key."""
        client = LgHdcpClient(
            host,
            "",
            async_get_clientsession(self.hass),
        )
        try:
            await client.async_request_pairing_key()
        except HdcpConnectionError as err:
            _LOGGER.debug("Pairing request to %s failed: %s", host, err)
            return "cannot_connect"
        except HdcpAuthError as err:
            _LOGGER.debug("The TV rejected the pairing request: %s", err)
            return "pairing_rejected"
        except HdcpProtocolError as err:
            _LOGGER.debug("The TV returned an unexpected pairing response: %s", err)
            return "protocol_error"
        except HdcpError as err:
            _LOGGER.debug("Unexpected pairing error: %s", err)
            return "unknown"
        finally:
            await client.async_close()
        return None

    async def _async_validate_key(self, host: str, key: str) -> str | None:
        """Validate a pairing key by requesting a session."""
        client = LgHdcpClient(
            host,
            key,
            async_get_clientsession(self.hass),
        )
        try:
            await client.async_authenticate()
        except HdcpAuthError as err:
            _LOGGER.debug("The TV rejected the pairing key: %s", err)
            return "invalid_auth"
        except HdcpConnectionError as err:
            _LOGGER.debug("Pairing key validation for %s failed: %s", host, err)
            return "cannot_connect"
        except HdcpProtocolError as err:
            _LOGGER.debug("The TV returned an unexpected auth response: %s", err)
            return "protocol_error"
        except HdcpError as err:
            _LOGGER.debug("Unexpected pairing key validation error: %s", err)
            return "unknown"
        finally:
            await client.async_close()
        return None
