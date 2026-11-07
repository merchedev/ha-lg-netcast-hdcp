"""Shared state tracking for LG NetCast HDCP televisions.

The HDCP protocol exposes the current channel and UI mode, but it does not
report the active HDMI input or the volume. This tracker combines the data
queries with commands sent by the integration and optional key events from an
external IR receiver.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Final

from .keys import HDCP_KEY_ALIASES, HDCP_KEYS
from .profiles import normalize_source_name

KEY_SEQUENCE_TIMEOUT: Final = 5.0
CHANNEL_ENTRY_TIMEOUT: Final = 3.0
_UNSET: Final = object()

_CODE_TO_KEY: Final[dict[str, str]] = {code: name for name, code in HDCP_KEYS.items()}
for _alias, _code in HDCP_KEY_ALIASES.items():
    _CODE_TO_KEY.setdefault(_code, _alias)


def resolve_key_name(value: str) -> str | None:
    """Resolve a key name or code to its canonical key name."""
    candidate = str(value).strip().upper()
    if candidate in HDCP_KEYS:
        return candidate
    if candidate in HDCP_KEY_ALIASES:
        return _CODE_TO_KEY.get(HDCP_KEY_ALIASES[candidate])
    if candidate.isdigit() and len(candidate) in (2, 3):
        return _CODE_TO_KEY.get(candidate)
    return None


class TvStateTracker:
    """Track the best-known state of a television."""

    def __init__(
        self,
        input_sources: dict[str, list[str]] | None = None,
        direct_input_keys: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize the tracker."""
        self.power: bool | None = False
        self.source: str | None = None
        self.channel: str | None = None
        self.channel_name: str | None = None
        self.muted = False
        self.ui_mode: str | None = None

        self._sources: dict[str, list[str]] = {}
        self._direct_input_keys: dict[str, str] = {
            key_name.upper(): source_name
            for source_name, key_name in (direct_input_keys or {}).items()
        }
        self._listeners: list[Callable[[], None]] = []
        self._key_buffer: list[str] = []
        self._channel_buffer = ""
        self._last_key_time: float | None = None
        self._last_digit_time: float | None = None

        for name, sequence in (input_sources or {}).items():
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(sequence, list) or not sequence:
                continue

            keys: list[str] = []
            for key in sequence:
                resolved = resolve_key_name(key)
                if resolved is None:
                    keys = []
                    break
                keys.append(resolved)

            if keys:
                self._sources[name.strip()] = keys

        self._sequence_keys = {
            key for sequence in self._sources.values() for key in sequence
        }
        self._max_sequence = max(
            (len(sequence) for sequence in self._sources.values()), default=0
        )

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener and return an unsubscribe callback."""
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    def process_sent_key(self, value: str, *, now: float | None = None) -> bool:
        """Process a key that the integration sent to the television."""
        key = resolve_key_name(value)
        if key is None:
            return False

        before = self._snapshot()
        if key == "POWER":
            self._toggle_power()
        else:
            self.power = True
            self._handle_key(key, now)
        self._notify_if_changed(before)
        return True

    def process_ir_key(self, value: str, *, now: float | None = None) -> bool:
        """Process a key observed by an external IR receiver."""
        key = resolve_key_name(value)
        if key is None:
            return False

        before = self._snapshot()
        if key == "POWER":
            self._toggle_power()
        else:
            self._handle_key(key, now)
        self._notify_if_changed(before)
        return True

    def apply(
        self,
        *,
        power: Any = _UNSET,
        source: Any = _UNSET,
        channel: Any = _UNSET,
        channel_name: Any = _UNSET,
        muted: Any = _UNSET,
        ui_mode: Any = _UNSET,
    ) -> None:
        """Apply state read from the television."""
        before = self._snapshot()
        if power is not _UNSET:
            self.power = power
        if source is not _UNSET:
            self.source = source
        if channel is not _UNSET:
            self.channel = channel
        if channel_name is not _UNSET:
            self.channel_name = channel_name
        if muted is not _UNSET:
            self.muted = muted
        if ui_mode is not _UNSET:
            self.ui_mode = ui_mode
        self._notify_if_changed(before)

    def set_power(self, power: bool | None) -> None:
        """Set the power state."""
        self.apply(power=power)

    def set_source(self, source: str | None, *, clear_channel: bool = True) -> None:
        """Set the current source, optionally clearing the channel."""
        if clear_channel:
            self.apply(source=source, channel=None, channel_name=None)
        else:
            self.apply(source=source)

    def restore(
        self,
        *,
        source: str | None = None,
        channel: str | None = None,
        channel_name: str | None = None,
        muted: bool | None = None,
        ui_mode: str | None = None,
    ) -> None:
        """Restore useful state after a Home Assistant restart."""
        before = self._snapshot()

        if self.power is False:
            if isinstance(channel, str):
                self.channel = channel
            if isinstance(channel_name, str):
                self.channel_name = channel_name

        if isinstance(source, str) and (self.power is False or self.channel is None):
            self.source = source

        if isinstance(muted, bool):
            self.muted = muted

        if isinstance(ui_mode, str) and self.ui_mode is None:
            self.ui_mode = ui_mode

        self._notify_if_changed(before)

    def _handle_key(self, key: str, now: float | None) -> None:
        """Update state from a non-power key."""
        timestamp = time.monotonic() if now is None else now
        if (
            self._last_key_time is not None
            and timestamp - self._last_key_time > KEY_SEQUENCE_TIMEOUT
        ):
            self._key_buffer.clear()
        self._last_key_time = timestamp

        if not key.startswith("NUMBER_"):
            self._channel_buffer = ""
            self._last_digit_time = None

        if key == "MUTE":
            self.muted = not self.muted
            return

        if key.startswith("NUMBER_"):
            self.source = None
            self.channel = self._append_channel(key[-1], timestamp)
            self.channel_name = None
            self._key_buffer.clear()
            return

        if key in ("CHANNEL_UP", "CHANNEL_DOWN"):
            self.source = None
            self.channel = self._step_channel(key)
            self.channel_name = None
            self._key_buffer.clear()
            return

        if key in self._direct_input_keys:
            self.source = self._source_name_for_key(key, self._direct_input_keys[key])
            self.channel = None
            self.channel_name = None
            self._key_buffer.clear()
            return

        if key in ("TV_RADIO", "LIST", "FAVORITE_CHANNEL"):
            self.source = None
            self.channel = None
            self.channel_name = None
            self._key_buffer.clear()
            return

        if key in ("HOME", "EXIT") and key not in self._sequence_keys:
            self._key_buffer.clear()
            return

        if key == "INPUT":
            self._key_buffer = [key]
            self._trim_key_buffer()
            self._match_input_sequence()
            return

        if key in self._sequence_keys:
            self._key_buffer.append(key)
            self._trim_key_buffer()
            self._match_input_sequence()

    def _toggle_power(self) -> None:
        """Toggle the assumed power state."""
        self.power = self.power is not True
        self._key_buffer.clear()
        self._channel_buffer = ""
        self._last_digit_time = None

    def _append_channel(self, digit: str, now: float) -> str | None:
        """Append a channel digit and return the normalized channel."""
        if (
            self._last_digit_time is None
            or now - self._last_digit_time > CHANNEL_ENTRY_TIMEOUT
        ):
            self._channel_buffer = ""

        self._channel_buffer += digit
        self._last_digit_time = now

        try:
            return str(int(self._channel_buffer))
        except ValueError:
            return None

    def _step_channel(self, key: str) -> str | None:
        """Step the channel up or down when it is known."""
        if self.channel is None or not self.channel.isdigit():
            return None

        step = 1 if key == "CHANNEL_UP" else -1
        return str(max(int(self.channel) + step, 0))

    def _source_name_for_key(self, key: str, fallback: str) -> str:
        """Return the configured source name for a direct-input key."""
        normalized = normalize_source_name(key)
        for name in self._sources:
            if normalize_source_name(name) == normalized:
                return name
        return fallback

    def _trim_key_buffer(self) -> None:
        """Keep only the longest configured sequence length."""
        if self._max_sequence and len(self._key_buffer) > self._max_sequence:
            self._key_buffer = self._key_buffer[-self._max_sequence :]

    def _match_input_sequence(self) -> None:
        """Update the source when the recent keys match a configured sequence."""
        for name, sequence in sorted(
            self._sources.items(), key=lambda item: len(item[1]), reverse=True
        ):
            if self._key_buffer[-len(sequence) :] == sequence:
                self.source = name
                self.channel = None
                self.channel_name = None
                self._key_buffer.clear()
                return

    def _snapshot(self) -> tuple[Any, ...]:
        """Return the tracked fields for change detection."""
        return (
            self.power,
            self.source,
            self.channel,
            self.channel_name,
            self.muted,
            self.ui_mode,
        )

    def _notify_if_changed(self, before: tuple[Any, ...]) -> None:
        """Notify listeners when a tracked field changed."""
        if self._snapshot() == before:
            return
        for listener in list(self._listeners):
            listener()
