"""Media player entity for LG NetCast HDCP televisions."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.trigger import PluggableAction

from . import LgNetcastHdcpConfigEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .hdcp import HdcpAuthError, HdcpError
from .triggers.turn_on import async_get_turn_on_trigger

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LgNetcastHdcpConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media player entity."""
    async_add_entities([LgNetcastHdcpMediaPlayer(entry)])


class LgNetcastHdcpMediaPlayer(MediaPlayerEntity):
    """Representation of an LG NetCast HDCP television."""

    _attr_assumed_state = True
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_has_entity_name = True
    _attr_media_content_type = MediaType.CHANNEL
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, entry: LgNetcastHdcpConfigEntry) -> None:
        """Initialize the media player."""
        self._entry = entry
        self._client = entry.runtime_data.client
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
        )
        self._attr_state = MediaPlayerState.OFF
        self._attr_is_volume_muted = False
        self._turn_on = PluggableAction(self.async_write_ha_state)

    async def async_added_to_hass(self) -> None:
        """Register the turn-on trigger and probe the TV."""
        await super().async_added_to_hass()

        registry_entry = self.registry_entry
        if registry_entry is not None and registry_entry.device_id is not None:
            self.async_on_remove(
                self._turn_on.async_register(
                    self.hass,
                    async_get_turn_on_trigger(registry_entry.device_id),
                )
            )

        try:
            await self._client.async_authenticate()
        except HdcpAuthError:
            _LOGGER.debug("The TV rejected the stored pairing key")
            self._entry.async_start_reauth(self.hass)
        except HdcpError:
            _LOGGER.debug("The TV is not reachable during setup")
        else:
            self._attr_state = MediaPlayerState.ON
            self.async_write_ha_state()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return supported media player features."""
        return SUPPORTED_FEATURES

    async def async_turn_on(self) -> None:
        """Run the configured external power-on action."""
        await self._turn_on.async_run(self.hass, self._context)

    async def async_turn_off(self) -> None:
        """Turn the TV off."""
        await self._async_send("POWER")
        self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Increase the volume."""
        await self._async_send("VOLUME_UP")

    async def async_volume_down(self) -> None:
        """Decrease the volume."""
        await self._async_send("VOLUME_DOWN")

    async def async_mute_volume(self, mute: bool) -> None:
        """Toggle mute when the requested state differs."""
        if mute == self._attr_is_volume_muted:
            return

        await self._async_send("MUTE")
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_media_play(self) -> None:
        """Send play."""
        await self._async_send("PLAY")

    async def async_media_pause(self) -> None:
        """Send pause."""
        await self._async_send("PAUSE")

    async def async_media_stop(self) -> None:
        """Send stop."""
        await self._async_send("STOP")

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Tune to a channel by sending its digits and OK."""
        if media_type != MediaType.CHANNEL:
            raise ValueError(f"Unsupported media type: {media_type}")

        digits = [character for character in str(media_id) if character.isdigit()]
        if not digits:
            raise ValueError(f"Invalid channel: {media_id}")

        await self._async_send_sequence(
            [f"NUMBER_{digit}" for digit in digits] + ["OK"]
        )

    async def _async_send(self, key: str) -> None:
        """Send a single key and update the assumed state."""
        try:
            await self._client.async_send_key(key)
        except HdcpAuthError:
            self._attr_state = MediaPlayerState.OFF
            self._entry.async_start_reauth(self.hass)
        except HdcpError:
            self._attr_state = MediaPlayerState.OFF
        else:
            self._attr_state = MediaPlayerState.ON
        self.async_write_ha_state()

    async def _async_send_sequence(self, keys: list[str]) -> None:
        """Send a key sequence and update the assumed state."""
        try:
            await self._client.async_send_sequence(keys)
        except HdcpAuthError:
            self._attr_state = MediaPlayerState.OFF
            self._entry.async_start_reauth(self.hass)
        except HdcpError:
            self._attr_state = MediaPlayerState.OFF
        else:
            self._attr_state = MediaPlayerState.ON
        self.async_write_ha_state()
