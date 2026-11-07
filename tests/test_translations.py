"""Tests for translation file consistency."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TRANSLATIONS = Path("custom_components/lg_netcast_hdcp/translations")
PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested translation mapping."""
    flat: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        flat[path] = item
        if isinstance(item, dict):
            flat.update(_flatten(item, path))
    return flat


def _placeholders(value: str) -> set[str]:
    """Return the placeholder names used in a translation string."""
    return set(PLACEHOLDER.findall(value))


async def test_spanish_translation_matches_english() -> None:
    """Every English key exists in Spanish with the same placeholders."""
    english = _flatten(json.loads((TRANSLATIONS / "en.json").read_text()))
    spanish = _flatten(json.loads((TRANSLATIONS / "es.json").read_text()))

    assert set(english) == set(spanish)
    for key, english_value in english.items():
        spanish_value = spanish[key]
        if isinstance(english_value, str) and isinstance(spanish_value, str):
            assert _placeholders(english_value) == _placeholders(spanish_value), key
