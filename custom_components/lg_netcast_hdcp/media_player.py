"""Media player entity for LG NetCast HDCP televisions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.service import async_call_from_config

from . import LgNetcastHdcpConfigEntry
from .const import (
    CONF_INPUT_SOURCES,
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
    MANUFACTURER,
    MODEL,
    POWER_OFF_SOURCE_DELAY,
    POWER_ON_REFRESH_DELAY,
    TURN_ON_METHOD_ACTION,
    TURN_ON_METHOD_BOTH,
    TURN_ON_METHOD_NONE,
    TURN_ON_METHOD_WOL,
)
from .hdcp import HdcpAuthError, HdcpError
from .profiles import normalize_source_name
from .wol import async_send_magic_packet

_LOGGER = logging.getLogger(__name__)

BASE_FEATURES = (
    MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LgNetcastHdcpConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media player entity."""
    async_add_entities([LgNetcastHdcpMediaPlayer(entry)])


class LgNetcastHdcpMediaPlayer(MediaPlayerEntity, RestoreEntity):
    """Representation of an LG NetCast HDCP television."""

    _attr_assumed_state = True
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, entry: LgNetcastHdcpConfigEntry) -> None:
        """Initialize the media player."""
        self._entry = entry
        self._client = entry.runtime_data.client
        self._tracker = entry.runtime_data.tracker
        self._options = entry.options
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
        )
        self._attr_state = MediaPlayerState.OFF
        self._attr_is_volume_muted = False
        self._attr_source: str | None = None
        self._attr_media_channel: str | None = None
        self._attr_media_title: str | None = None

    async def async_added_to_hass(self) -> None:
        """Register for tracker updates and restore the last state."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._tracker.async_add_listener(self._handle_tracker_update)
        )

        if (last_state := await self.async_get_last_state()) is not None:
            last_channel = last_state.attributes.get("media_channel")
            self._tracker.restore(
                source=last_state.attributes.get("source"),
                channel=last_channel,
                channel_name=(
                    last_state.attributes.get("media_title") if last_channel else None
                ),
                muted=last_state.attributes.get("is_volume_muted"),
                ui_mode=last_state.attributes.get("ui_mode"),
            )

        self._handle_tracker_update()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return supported media player features."""
        features = BASE_FEATURES
        if self._turn_on_method != TURN_ON_METHOD_NONE:
            features |= MediaPlayerEntityFeature.TURN_ON
        if self.source_list:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE
        return features

    @property
    def source_list(self) -> list[str] | None:
        """Return configured sources plus confirmed direct inputs."""
        sources = list(self._input_sources)
        known = {normalize_source_name(name) for name in sources}
        for name in self._client.profile.direct_input_keys:
            if normalize_source_name(name) not in known:
                sources.append(name)
        return sources or None

    @property
    def source(self) -> str | None:
        """Return the last selected source."""
        return self._attr_source

    @property
    def media_content_type(self) -> MediaType | None:
        """Return the media type for the current channel."""
        return MediaType.CHANNEL if self._attr_media_channel else None

    @property
    def media_content_id(self) -> str | None:
        """Return the current channel."""
        return self._attr_media_channel

    @property
    def media_channel(self) -> str | None:
        """Return the current channel."""
        return self._attr_media_channel

    @property
    def media_title(self) -> str | None:
        """Return the current channel name."""
        return self._attr_media_title

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes: dict[str, Any] = {}
        if self._tracker.power is True and self._tracker.ui_mode:
            attributes["ui_mode"] = self._tracker.ui_mode
        return attributes

    @property
    def _turn_on_method(self) -> str:
        """Return the configured power-on method."""
        return self._options.get(CONF_TURN_ON_METHOD, DEFAULT_TURN_ON_METHOD)

    @property
    def _input_sources(self) -> dict[str, list[str]]:
        """Return configured input sources."""
        sources = self._options.get(CONF_INPUT_SOURCES, {})
        return sources if isinstance(sources, dict) else {}

    @property
    def _power_off_source(self) -> str:
        """Return the source to select before power off."""
        source = self._options.get(CONF_POWER_OFF_SOURCE, "")
        return source.strip() if isinstance(source, str) else ""

    async def async_turn_on(self) -> None:
        """Power on the TV using the configured method."""
        method = self._turn_on_method
        if method == TURN_ON_METHOD_NONE:
            raise HomeAssistantError("No power-on method is configured")

        if method in (TURN_ON_METHOD_WOL, TURN_ON_METHOD_BOTH):
            await async_send_magic_packet(
                self.hass,
                self._options.get(CONF_WOL_MAC, ""),
                self._options.get(CONF_WOL_BROADCAST, DEFAULT_WOL_BROADCAST),
                self._options.get(CONF_WOL_PORT, DEFAULT_WOL_PORT),
            )

        if method in (TURN_ON_METHOD_ACTION, TURN_ON_METHOD_BOTH):
            await self._async_run_turn_on_action()

        self._tracker.set_power(True)
        self.async_on_remove(
            async_call_later(
                self.hass,
                POWER_ON_REFRESH_DELAY,
                HassJob(
                    self._async_refresh_after_power_on,
                    "LG TV state refresh after power on",
                    cancel_on_shutdown=True,
                ),
            )
        )

    async def _async_refresh_after_power_on(self, _now) -> None:
        """Refresh state after the TV has had time to boot."""
        await self._entry.runtime_data.coordinator.async_request_refresh()

    async def _async_run_turn_on_action(self) -> None:
        """Run the configured custom turn-on action."""
        actions = self._options.get(CONF_TURN_ON_ACTION, [])
        if not actions:
            raise HomeAssistantError("No turn-on action is configured")

        for action in actions:
            await async_call_from_config(
                self.hass,
                action,
                blocking=True,
                context=self._context,
            )

    async def async_turn_off(self) -> None:
        """Turn the TV off, optionally selecting a CEC source first."""
        source = self._power_off_source
        if source:
            await self._async_select_power_off_source(source)

        await self._async_send("POWER")
        self._tracker.set_power(False)

    async def _async_select_power_off_source(self, source: str) -> None:
        """Select the configured source before entering standby."""
        configured_source = next(
            (
                name
                for name in self._input_sources
                if normalize_source_name(name) == normalize_source_name(source)
            ),
            None,
        )
        direct_source = self._client.profile.direct_input_source(source)

        if configured_source is not None:
            source = configured_source
            sequence = self._input_sources[source]
            direct_key = self._client.profile.direct_input_key(source)
        elif direct_source is not None:
            source = direct_source
            sequence = None
            direct_key = self._client.profile.direct_input_key(source)
        else:
            _LOGGER.debug(
                "Power-off source %s is not a direct input or configured source",
                source,
            )
            return

        if direct_key is not None:
            try:
                await self._async_send(direct_key)
            except HomeAssistantError as err:
                if err.translation_key == "session_rejected":
                    raise
                _LOGGER.debug(
                    "Could not select power-off source %s: %s",
                    source,
                    err,
                )
                return
            await asyncio.sleep(POWER_OFF_SOURCE_DELAY)
            self._tracker.set_source(source)
            return

        if not sequence:
            _LOGGER.debug(
                "Power-off source %s has no configured sequence",
                source,
            )
            return

        try:
            await self._async_send_sequence(sequence)
        except HomeAssistantError as err:
            if err.translation_key == "session_rejected":
                raise
            _LOGGER.debug(
                "Could not select power-off source %s: %s",
                source,
                err,
            )
            return
        await asyncio.sleep(POWER_OFF_SOURCE_DELAY)
        self._tracker.set_source(source)

    async def async_volume_up(self) -> None:
        """Increase the volume."""
        await self._async_send("VOLUME_UP")

    async def async_volume_down(self) -> None:
        """Decrease the volume."""
        await self._async_send("VOLUME_DOWN")

    async def async_mute_volume(self, mute: bool) -> None:
        """Toggle mute when the requested state differs."""
        if mute == self._tracker.muted:
            return

        await self._async_send("MUTE")

    async def async_select_source(self, source: str) -> None:
        """Select an input source using a direct key or key sequence."""
        configured_source = next(
            (
                name
                for name in self._input_sources
                if normalize_source_name(name) == normalize_source_name(source)
            ),
            None,
        )
        direct_source = self._client.profile.direct_input_source(source)

        if configured_source is not None:
            source = configured_source
            sequence = self._input_sources[source]
            direct_key = self._client.profile.direct_input_key(source)
        elif direct_source is not None:
            source = direct_source
            sequence = None
            direct_key = self._client.profile.direct_input_key(source)
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_source",
                translation_placeholders={"source": source},
            )

        if direct_key is not None:
            await self._async_send(direct_key)
            self._tracker.set_source(source)
            return

        if not sequence:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_source",
                translation_placeholders={"source": source},
            )

        await self._async_send_sequence(sequence)
        self._tracker.set_source(source)

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

    async def async_process_ir_key(self, key: str) -> None:
        """Update the assumed state from an external IR receiver key."""
        if not self._tracker.process_ir_key(key):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unsupported_ir_key",
                translation_placeholders={"key": key},
            )

    def _handle_tracker_update(self) -> None:
        """Copy tracker state to Home Assistant attributes."""
        power = self._tracker.power
        if power is True:
            self._attr_state = MediaPlayerState.ON
        elif power is False:
            self._attr_state = MediaPlayerState.OFF
        else:
            self._attr_state = STATE_UNKNOWN

        self._attr_source = self._tracker.source
        self._attr_media_channel = self._tracker.channel
        if self._tracker.channel:
            self._attr_media_title = (
                self._tracker.channel_name or f"Channel {self._tracker.channel}"
            )
        elif self._tracker.source:
            self._attr_media_title = self._tracker.source
        else:
            self._attr_media_title = None
        self._attr_is_volume_muted = self._tracker.muted
        self.async_write_ha_state()

    async def _async_send(self, key: str) -> None:
        """Send a single key and update the assumed state."""
        try:
            await self._client.async_send_key(key)
        except HdcpAuthError as err:
            _LOGGER.warning(
                "The TV rejected the session while sending %s: %s",
                key,
                err,
            )
            self._tracker.set_power(None)
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="session_rejected",
            ) from err
        except HdcpError as err:
            _LOGGER.warning("Could not send %s to the TV: %s", key, err)
            self._tracker.set_power(None)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
        else:
            self._tracker.process_sent_key(key)

    async def _async_send_sequence(self, keys: list[str]) -> None:
        """Send a key sequence and update the assumed state."""
        try:
            await self._client.async_send_sequence(keys)
        except HdcpAuthError as err:
            _LOGGER.warning(
                "The TV rejected the session while sending a key sequence: %s",
                err,
            )
            self._tracker.set_power(None)
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="session_rejected",
            ) from err
        except HdcpError as err:
            _LOGGER.warning("Could not send a key sequence to the TV: %s", err)
            self._tracker.set_power(None)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
        else:
            for key in keys:
                self._tracker.process_sent_key(key)
