"""Tests for the verified decimal key map."""

from __future__ import annotations

from custom_components.lg_netcast_hdcp.keys import HDCP_KEYS


def test_number_codes_skip_the_letter_gap() -> None:
    """Number keys use the verified decimal codes."""
    assert [HDCP_KEYS[f"NUMBER_{digit}"] for digit in range(10)] == [
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
    ]


def test_confirmed_navigation_and_menu_codes() -> None:
    """The main menu/navigation codes match the tested model."""
    assert HDCP_KEYS["HOME"] == "67"
    assert HDCP_KEYS["OK"] == "68"
    assert HDCP_KEYS["INPUT"] == "11"
    assert HDCP_KEYS["Q_MENU"] == "10"
    assert HDCP_KEYS["EXIT"] == "40"
    assert HDCP_KEYS["LEFT"] == "07"
    assert HDCP_KEYS["RIGHT"] == "06"
