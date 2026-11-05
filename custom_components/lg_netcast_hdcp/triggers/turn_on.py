"""Device turn-on trigger for LG NetCast HDCP televisions."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import (
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.trigger import (
    PluggableAction,
    TriggerActionType,
    TriggerInfo,
)
from homeassistant.helpers.typing import ConfigType

from ..const import DOMAIN

PLATFORM_TYPE = f"{DOMAIN}.turn_on"

TRIGGER_SCHEMA = vol.All(
    cv.TRIGGER_BASE_SCHEMA.extend(
        {
            vol.Required(CONF_PLATFORM): PLATFORM_TYPE,
            vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        }
    ),
    cv.has_at_least_one_key(ATTR_ENTITY_ID, ATTR_DEVICE_ID),
)


def async_get_turn_on_trigger(device_id: str) -> dict[str, str]:
    """Return the device trigger configuration for a TV."""
    return {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: device_id,
        CONF_DOMAIN: DOMAIN,
        CONF_TYPE: PLATFORM_TYPE,
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
    *,
    platform_type: str = PLATFORM_TYPE,
) -> CALLBACK_TYPE | None:
    """Attach a turn-on trigger."""
    device_ids: set[str] = set(config.get(ATTR_DEVICE_ID, []))

    if ATTR_ENTITY_ID in config:
        entity_registry = er.async_get(hass)
        for entity_id in config[ATTR_ENTITY_ID]:
            entity_entry = entity_registry.async_get(entity_id)
            if (
                entity_entry is None
                or entity_entry.device_id is None
                or entity_entry.platform != DOMAIN
            ):
                raise ValueError(f"Entity {entity_id} is not a valid {DOMAIN} entity")
            device_ids.add(entity_entry.device_id)

    trigger_data = trigger_info["trigger_data"]
    unsubs: list[CALLBACK_TYPE] = []

    for device_id in device_ids:
        device = dr.async_get(hass).async_get(device_id)
        device_name = (
            (device.name_by_user or device.name) if device is not None else device_id
        )

        variables: dict[str, Any] = {
            **trigger_data,
            CONF_PLATFORM: platform_type,
            ATTR_DEVICE_ID: device_id,
            "description": f"LG NetCast HDCP turn on trigger for {device_name}",
        }

        unsubs.append(
            PluggableAction.async_attach_trigger(
                hass,
                async_get_turn_on_trigger(device_id),
                action,
                {"trigger": variables},
            )
        )

    @callback
    def async_remove() -> None:
        """Remove the trigger listener."""
        while unsubs:
            unsubs.pop()()

    return async_remove
