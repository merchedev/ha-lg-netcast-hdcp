"""Tests for the shared television state tracker."""

from __future__ import annotations

from custom_components.lg_netcast_hdcp.state import TvStateTracker


def test_power_toggles() -> None:
    """Power keys toggle the assumed power state."""
    tracker = TvStateTracker()

    assert tracker.process_ir_key("POWER") is True
    assert tracker.power is True
    assert tracker.process_ir_key("POWER") is True
    assert tracker.power is False

    assert tracker.process_sent_key("POWER") is True
    assert tracker.power is True


def test_sent_key_marks_power_on() -> None:
    """Any successfully sent non-power key implies the TV is on."""
    tracker = TvStateTracker()
    tracker.set_power(False)

    assert tracker.process_sent_key("VOLUME_UP") is True
    assert tracker.power is True


def test_direct_input_key_updates_source() -> None:
    """Direct HDMI keys select the configured source name."""
    tracker = TvStateTracker(
        {
            "HDMI1": ["INPUT", "LEFT", "OK"],
            "HDMI 2": ["INPUT", "LEFT", "LEFT", "OK"],
        },
        {"HDMI1": "HDMI1", "HDMI2": "HDMI2"},
    )
    tracker.apply(channel="21", channel_name="VEO 7")

    assert tracker.process_ir_key("HDMI1") is True
    assert tracker.source == "HDMI1"
    assert tracker.channel is None
    assert tracker.channel_name is None

    assert tracker.process_ir_key("HDMI_2") is True
    assert tracker.source == "HDMI 2"


def test_input_sequence_updates_source() -> None:
    """A configured input sequence is recognised from observed keys."""
    tracker = TvStateTracker({"HDMI1": ["INPUT", "LEFT", "OK"]})

    assert tracker.process_ir_key("INPUT", now=0.0) is True
    assert tracker.process_ir_key("LEFT", now=0.2) is True
    assert tracker.source is None
    assert tracker.process_ir_key("OK", now=0.4) is True
    assert tracker.source == "HDMI1"


def test_nonmatching_sequence_keeps_source() -> None:
    """A different navigation sequence does not change the source."""
    tracker = TvStateTracker({"HDMI1": ["INPUT", "LEFT", "OK"]})

    tracker.process_ir_key("INPUT", now=0.0)
    tracker.process_ir_key("RIGHT", now=0.2)
    tracker.process_ir_key("OK", now=0.4)

    assert tracker.source is None


def test_channel_digits_and_timeout() -> None:
    """Channel digits are accumulated and reset after the entry timeout."""
    tracker = TvStateTracker()

    tracker.process_ir_key("NUMBER_2", now=0.0)
    tracker.process_ir_key("NUMBER_1", now=1.0)
    assert tracker.channel == "21"
    assert tracker.source is None

    tracker.process_ir_key("NUMBER_5", now=10.0)
    assert tracker.channel == "5"


def test_channel_entry_resets_after_another_key() -> None:
    """A non-digit key cancels the current channel entry."""
    tracker = TvStateTracker()

    tracker.process_ir_key("NUMBER_2", now=0.0)
    tracker.process_ir_key("HDMI1", now=0.5)
    tracker.process_ir_key("NUMBER_5", now=1.0)

    assert tracker.channel == "5"


def test_channel_up_and_down() -> None:
    """Channel up and down step the known channel."""
    tracker = TvStateTracker()
    tracker.apply(channel="21")

    tracker.process_ir_key("CHANNEL_UP")
    assert tracker.channel == "22"
    tracker.process_ir_key("CHANNEL_DOWN")
    assert tracker.channel == "21"

    tracker.apply(channel=None)
    tracker.process_ir_key("CHANNEL_UP")
    assert tracker.channel is None


def test_mute_toggles() -> None:
    """Mute keys toggle the mute state."""
    tracker = TvStateTracker()

    tracker.process_ir_key("MUTE")
    assert tracker.muted is True
    tracker.process_ir_key("MUTE")
    assert tracker.muted is False


def test_restore_off_state() -> None:
    """The last channel and source are restored when the TV is off."""
    tracker = TvStateTracker()
    tracker.set_power(False)

    tracker.restore(
        source="HDMI1",
        channel="21",
        channel_name="VEO 7",
        muted=True,
        ui_mode="VolCh",
    )

    assert tracker.source == "HDMI1"
    assert tracker.channel == "21"
    assert tracker.channel_name == "VEO 7"
    assert tracker.muted is True
    assert tracker.ui_mode == "VolCh"


def test_restore_on_external_input_keeps_source() -> None:
    """The last source is useful when the TV is on an external input."""
    tracker = TvStateTracker()
    tracker.set_power(True)
    tracker.apply(channel=None)

    tracker.restore(source="HDMI1", channel="21", channel_name="VEO 7")

    assert tracker.source == "HDMI1"
    assert tracker.channel is None


def test_restore_does_not_override_fresh_tv_state() -> None:
    """Fresh channel data wins over the restored state."""
    tracker = TvStateTracker()
    tracker.set_power(True)
    tracker.apply(channel="21", channel_name="VEO 7")

    tracker.restore(source="HDMI1", channel="22", channel_name="Other")

    assert tracker.source is None
    assert tracker.channel == "21"
    assert tracker.channel_name == "VEO 7"


def test_listeners_fire_only_on_changes() -> None:
    """Listeners are not called for keys that do not change tracked state."""
    tracker = TvStateTracker()
    calls: list[str] = []
    tracker.async_add_listener(lambda: calls.append("changed"))

    tracker.process_sent_key("VOLUME_UP")
    assert len(calls) == 1
    tracker.process_sent_key("VOLUME_UP")
    assert len(calls) == 1


def test_unknown_key_is_rejected() -> None:
    """Unknown keys are not processed."""
    tracker = TvStateTracker()

    assert tracker.process_ir_key("NOT_A_KEY") is False
    assert tracker.process_sent_key("NOT_A_KEY") is False
