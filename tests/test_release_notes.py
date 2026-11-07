"""Tests for release-note extraction."""

from __future__ import annotations

import json

import pytest
from tools.extract_release_notes import (
    extract_release_notes,
    normalize_version,
    read_manifest_version,
)

CHANGELOG = """# Changelog

## 0.4.1

- Added HDMI buttons.
- Documented the IR receiver.

## 0.4.0

- Added state tracking.
"""


def test_normalize_version() -> None:
    """Tags may be prefixed with v."""
    assert normalize_version("v0.4.1") == "0.4.1"
    assert normalize_version("0.4.1") == "0.4.1"


def test_extract_release_notes() -> None:
    """Only the requested version section is returned."""
    notes = extract_release_notes(CHANGELOG, "0.4.1")

    assert notes == "- Added HDMI buttons.\n- Documented the IR receiver."


def test_extract_missing_section() -> None:
    """A missing version produces no notes."""
    assert extract_release_notes(CHANGELOG, "9.9.9") == ""


def test_manifest_version(tmp_path) -> None:
    """The manifest version is read as a string."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": "0.4.1"}), encoding="utf-8")

    assert read_manifest_version(manifest) == "0.4.1"


def test_manifest_without_version(tmp_path) -> None:
    """A manifest without a version is rejected."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({}), encoding="utf-8")

    with pytest.raises(ValueError, match="does not contain a version"):
        read_manifest_version(manifest)
