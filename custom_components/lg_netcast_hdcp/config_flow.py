"""Config flow for the LG NetCast HDCP integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.network import is_host_valid

from .const import (
    CONF_INPUT_SOURCES,
    CONF_IR_STATE_TRACKING,
    CONF_PAIRING_KEY,
    CONF_POWER_OFF_SOURCE,
    CONF_TURN_ON_ACTION,
    CONF_TURN_ON_METHOD,
    CONF_WOL_BROADCAST,
    CONF_WOL_MAC,
    CONF_WOL_PORT,
    DEFAULT_TURN_ON_METHOD,
    DEFAULT_WOL_BROADCAST,
    DEFAULT_WOL_PORT,
    DOMAIN,
    PAIRING_KEY_LENGTH,
    PAIRING_KEY_PATTERN,
    TURN_ON_METHOD_ACTION,
    TURN_ON_METHOD_BOTH,
    TURN_ON_METHOD_WOL,
    TURN_ON_METHODS,
)
from .hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    HdcpError,
    LgHdcpClient,
)
from .profiles import DEFAULT_PROFILE, normalize_source_name
from .wol import normalize_mac

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
        except HdcpConnectionError:
            return "cannot_connect"
        except HdcpError:
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
        except HdcpAuthError:
            return "invalid_auth"
        except HdcpConnectionError:
            return "cannot_connect"
        except HdcpError:
            return "unknown"
        finally:
            await client.async_close()
        return None


class LgNetcastHdcpOptionsFlow(OptionsFlow):
    """Configure power-on behavior and input sources."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        current = self.config_entry.options
        errors: dict[str, str] = {}

        current_sources = current.get(CONF_INPUT_SOURCES, {})
        custom_source_names = (
            list(current_sources) if isinstance(current_sources, dict) else []
        )
        source_options: list[str] = []
        seen_sources: set[str] = set()
        for name in [
            *custom_source_names,
            *DEFAULT_PROFILE.direct_input_keys,
        ]:
            normalized = normalize_source_name(name)
            if normalized in seen_sources:
                continue
            seen_sources.add(normalized)
            source_options.append(name)

        current_power_off_source = current.get(CONF_POWER_OFF_SOURCE, "")
        if (
            current_power_off_source
            and normalize_source_name(current_power_off_source) not in seen_sources
        ):
            source_options.append(current_power_off_source)

        default_power_off_source = current_power_off_source or "(none)"
        if current_power_off_source:
            matching_option = next(
                (
                    name
                    for name in source_options
                    if normalize_source_name(name)
                    == normalize_source_name(current_power_off_source)
                ),
                None,
            )
            if matching_option is not None:
                default_power_off_source = matching_option

        if user_input is not None:
            method = user_input[CONF_TURN_ON_METHOD]
            mac = user_input.get(CONF_WOL_MAC, "").strip()
            action = user_input.get(CONF_TURN_ON_ACTION) or []
            sources, source_error = self._normalize_sources(
                user_input.get(CONF_INPUT_SOURCES)
            )
            power_off_source = str(
                user_input.get(CONF_POWER_OFF_SOURCE, "") or ""
            ).strip()
            if power_off_source == "(none)":
                power_off_source = ""
            ir_state_tracking = bool(user_input.get(CONF_IR_STATE_TRACKING, False))

            if source_error:
                errors[CONF_INPUT_SOURCES] = source_error
            elif power_off_source:
                valid_sources = [
                    *(sources or {}),
                    *DEFAULT_PROFILE.direct_input_keys,
                ]
                normalized_power_off_source = normalize_source_name(power_off_source)
                matching_source = next(
                    (
                        name
                        for name in valid_sources
                        if normalize_source_name(name) == normalized_power_off_source
                    ),
                    None,
                )
                if matching_source is None:
                    errors[CONF_POWER_OFF_SOURCE] = "unknown_source"
                else:
                    power_off_source = matching_source

            if not isinstance(action, list) or not all(
                isinstance(item, dict) for item in action
            ):
                errors[CONF_TURN_ON_ACTION] = "invalid_action"
            if method in (TURN_ON_METHOD_ACTION, TURN_ON_METHOD_BOTH) and not action:
                errors[CONF_TURN_ON_ACTION] = "action_required"
            if method in (TURN_ON_METHOD_WOL, TURN_ON_METHOD_BOTH):
                if not mac:
                    errors[CONF_WOL_MAC] = "mac_required"
                else:
                    try:
                        normalize_mac(mac)
                    except ValueError:
                        errors[CONF_WOL_MAC] = "invalid_mac"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_TURN_ON_METHOD: method,
                        CONF_WOL_MAC: mac,
                        CONF_WOL_BROADCAST: user_input.get(
                            CONF_WOL_BROADCAST, DEFAULT_WOL_BROADCAST
                        ).strip()
                        or DEFAULT_WOL_BROADCAST,
                        CONF_WOL_PORT: user_input.get(CONF_WOL_PORT, DEFAULT_WOL_PORT),
                        CONF_TURN_ON_ACTION: action,
                        CONF_INPUT_SOURCES: sources or {},
                        CONF_POWER_OFF_SOURCE: power_off_source,
                        CONF_IR_STATE_TRACKING: ir_state_tracking,
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TURN_ON_METHOD,
                        default=current.get(
                            CONF_TURN_ON_METHOD, DEFAULT_TURN_ON_METHOD
                        ),
                    ): vol.In(TURN_ON_METHODS),
                    vol.Optional(
                        CONF_WOL_MAC, default=current.get(CONF_WOL_MAC, "")
                    ): cv.string,
                    vol.Optional(
                        CONF_WOL_BROADCAST,
                        default=current.get(CONF_WOL_BROADCAST, DEFAULT_WOL_BROADCAST),
                    ): cv.string,
                    vol.Optional(
                        CONF_WOL_PORT,
                        default=current.get(CONF_WOL_PORT, DEFAULT_WOL_PORT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                    vol.Optional(
                        CONF_TURN_ON_ACTION,
                        default=current.get(CONF_TURN_ON_ACTION, []),
                    ): selector.ActionSelector(),
                    vol.Optional(
                        CONF_INPUT_SOURCES,
                        default=current.get(CONF_INPUT_SOURCES, {}),
                    ): selector.ObjectSelector(),
                    vol.Optional(
                        CONF_POWER_OFF_SOURCE,
                        default=default_power_off_source,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["(none)", *source_options],
                            custom_value=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_IR_STATE_TRACKING,
                        default=current.get(CONF_IR_STATE_TRACKING, False),
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def _normalize_sources(
        value: Any,
    ) -> tuple[dict[str, list[str]] | None, str | None]:
        """Validate and normalize the input source mapping."""
        if value in (None, {}):
            return {}, None
        if not isinstance(value, dict):
            return None, "invalid_sources"

        normalized: dict[str, list[str]] = {}
        for name, sequence in value.items():
            if not isinstance(name, str) or not name.strip():
                return None, "invalid_sources"
            if not isinstance(sequence, list) or not sequence:
                return None, "invalid_sources"

            keys: list[str] = []
            for key in sequence:
                if not isinstance(key, str) or not key.strip():
                    return None, "invalid_sources"
                keys.append(key.strip().upper())
            normalized[name.strip()] = keys

        return normalized, None
