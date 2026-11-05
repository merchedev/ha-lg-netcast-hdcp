"""Tests for the turn-on trigger definitions."""

from __future__ import annotations

from custom_components.lg_netcast_hdcp.device_trigger import (
    async_get_triggers,
)
from custom_components.lg_netcast_hdcp.triggers.turn_on import (
    TRIGGER_SCHEMA,
    async_get_turn_on_trigger,
)

DEVICE_ID = "device-id"


def test_turn_on_trigger_shape() -> None:
    """The trigger data uses the device trigger platform."""
    assert async_get_turn_on_trigger(DEVICE_ID) == {
        "platform": "device",
        "device_id": DEVICE_ID,
        "domain": "lg_netcast_hdcp",
        "type": "lg_netcast_hdcp.turn_on",
    }


def test_trigger_schema_accepts_entity_id() -> None:
    """The YAML trigger accepts an entity target."""
    config = TRIGGER_SCHEMA(
        {
            "platform": "lg_netcast_hdcp.turn_on",
            "entity_id": "media_player.lg_tv",
        }
    )
    assert config["entity_id"] == ["media_player.lg_tv"]


async def test_device_trigger_listing() -> None:
    """The device automation lists the turn-on trigger."""
    triggers = await async_get_triggers(None, DEVICE_ID)
    assert triggers == [async_get_turn_on_trigger(DEVICE_ID)]
