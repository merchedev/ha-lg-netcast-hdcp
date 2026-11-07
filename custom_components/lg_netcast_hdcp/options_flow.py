"""Options flow for the LG NetCast HDCP integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    CONF_INPUT_SOURCES,
    CONF_IR_STATE_TRACKING,
    CONF_POWER_OFF_SOURCE,
    CONF_TURN_ON_ACTION,
    CONF_TURN_ON_METHOD,
    CONF_WOL_BROADCAST,
    CONF_WOL_MAC,
    CONF_WOL_PORT,
    DEFAULT_TURN_ON_METHOD,
    DEFAULT_WOL_BROADCAST,
    DEFAULT_WOL_PORT,
    TURN_ON_METHOD_ACTION,
    TURN_ON_METHOD_BOTH,
    TURN_ON_METHOD_WOL,
    TURN_ON_METHODS,
)
from .profiles import DEFAULT_PROFILE, normalize_source_name
from .wol import normalize_mac

NONE_SOURCE = "(none)"


class LgNetcastHdcpOptionsFlow(OptionsFlow):
    """Configure power-on behavior, input sources, and state tracking."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["power_on", "sources", "tracking"],
        )

    async def async_step_power_on(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure how the TV is powered on."""
        current = self.config_entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            method = str(
                user_input.get(
                    CONF_TURN_ON_METHOD,
                    current.get(CONF_TURN_ON_METHOD, DEFAULT_TURN_ON_METHOD),
                )
            )
            mac = str(
                user_input.get(CONF_WOL_MAC, current.get(CONF_WOL_MAC, "")) or ""
            ).strip()
            action = (
                user_input.get(
                    CONF_TURN_ON_ACTION,
                    current.get(CONF_TURN_ON_ACTION, []),
                )
                or []
            )

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
                        **current,
                        CONF_TURN_ON_METHOD: method,
                        CONF_WOL_MAC: mac,
                        CONF_WOL_BROADCAST: (
                            str(
                                user_input.get(
                                    CONF_WOL_BROADCAST,
                                    current.get(
                                        CONF_WOL_BROADCAST, DEFAULT_WOL_BROADCAST
                                    ),
                                )
                                or ""
                            ).strip()
                            or DEFAULT_WOL_BROADCAST
                        ),
                        CONF_WOL_PORT: user_input.get(
                            CONF_WOL_PORT,
                            current.get(CONF_WOL_PORT, DEFAULT_WOL_PORT),
                        ),
                        CONF_TURN_ON_ACTION: action,
                    },
                )

        return self.async_show_form(
            step_id="power_on",
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
                }
            ),
            errors=errors,
        )

    async def async_step_sources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure input sources and the source before power off."""
        current = self.config_entry.options
        current_sources = current.get(CONF_INPUT_SOURCES, {})
        source_options = _source_options(
            current_sources,
            current.get(CONF_POWER_OFF_SOURCE, ""),
        )
        default_power_off_source = _default_power_off_source(
            current.get(CONF_POWER_OFF_SOURCE, ""),
            source_options,
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            sources, source_error = _normalize_sources(
                user_input.get(CONF_INPUT_SOURCES, current.get(CONF_INPUT_SOURCES))
            )
            power_off_source = str(
                user_input.get(
                    CONF_POWER_OFF_SOURCE,
                    current.get(CONF_POWER_OFF_SOURCE, ""),
                )
                or ""
            ).strip()
            if power_off_source == NONE_SOURCE:
                power_off_source = ""

            if source_error:
                errors[CONF_INPUT_SOURCES] = source_error
            elif power_off_source:
                valid_sources = [
                    *(sources or {}),
                    *DEFAULT_PROFILE.direct_input_keys,
                ]
                matching_source = next(
                    (
                        name
                        for name in valid_sources
                        if normalize_source_name(name)
                        == normalize_source_name(power_off_source)
                    ),
                    None,
                )
                if matching_source is None:
                    errors[CONF_POWER_OFF_SOURCE] = "unknown_source"
                else:
                    power_off_source = matching_source

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        **current,
                        CONF_INPUT_SOURCES: sources or {},
                        CONF_POWER_OFF_SOURCE: power_off_source,
                    },
                )

        return self.async_show_form(
            step_id="sources",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_INPUT_SOURCES,
                        default=current.get(CONF_INPUT_SOURCES, {}),
                    ): selector.ObjectSelector(),
                    vol.Optional(
                        CONF_POWER_OFF_SOURCE,
                        default=default_power_off_source,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[NONE_SOURCE, *source_options],
                            custom_value=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure optional IR receiver state tracking."""
        current = self.config_entry.options

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    **current,
                    CONF_IR_STATE_TRACKING: bool(
                        user_input.get(
                            CONF_IR_STATE_TRACKING,
                            current.get(CONF_IR_STATE_TRACKING, False),
                        )
                    ),
                },
            )

        return self.async_show_form(
            step_id="tracking",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_IR_STATE_TRACKING,
                        default=current.get(CONF_IR_STATE_TRACKING, False),
                    ): selector.BooleanSelector(),
                }
            ),
        )


def _source_options(
    current_sources: Any,
    current_power_off_source: Any,
) -> list[str]:
    """Return source names for the power-off selector."""
    custom_source_names = (
        list(current_sources) if isinstance(current_sources, dict) else []
    )
    source_options: list[str] = []
    seen_sources: set[str] = set()
    for name in [*custom_source_names, *DEFAULT_PROFILE.direct_input_keys]:
        normalized = normalize_source_name(name)
        if normalized in seen_sources:
            continue
        seen_sources.add(normalized)
        source_options.append(name)

    if (
        isinstance(current_power_off_source, str)
        and current_power_off_source
        and normalize_source_name(current_power_off_source) not in seen_sources
    ):
        source_options.append(current_power_off_source)

    return source_options


def _default_power_off_source(value: Any, source_options: list[str]) -> str:
    """Return the selector default for the power-off source."""
    if not isinstance(value, str) or not value:
        return NONE_SOURCE

    normalized = normalize_source_name(value)
    return next(
        (name for name in source_options if normalize_source_name(name) == normalized),
        NONE_SOURCE,
    )


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
