#!/usr/bin/env python3
"""Extract release notes for a tag from CHANGELOG.md.

The release workflow uses this script so the GitHub release body, and therefore
the Home Assistant update dialog, contains the actual changelog instead of only
an automatically generated compare link.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"
DEFAULT_MANIFEST = ROOT / "custom_components" / "lg_netcast_hdcp" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "release-notes.md"


def normalize_version(tag: str) -> str:
    """Return a version without a leading v."""
    return tag[1:] if tag.startswith("v") else tag


def extract_release_notes(changelog: str, version: str) -> str:
    """Return the CHANGELOG section for a version, excluding the heading."""
    heading = f"## {version}"
    capture = False
    notes: list[str] = []

    for line in changelog.splitlines():
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            notes.append(line)

    return "\n".join(notes).strip()


def read_manifest_version(path: Path) -> str:
    """Read and validate the integration version from the manifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{path} does not contain a version")
    return version


def main() -> int:
    """Run the extractor."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Git tag, for example v0.4.1")
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help="Path to CHANGELOG.md",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the release notes",
    )
    args = parser.parse_args()

    version = normalize_version(args.tag)
    manifest_version = read_manifest_version(args.manifest)
    if version != manifest_version:
        print(
            f"Tag {args.tag} does not match manifest version {manifest_version}",
            file=sys.stderr,
        )
        return 1

    notes = extract_release_notes(
        args.changelog.read_text(encoding="utf-8"),
        version,
    )
    if not notes:
        print(f"No CHANGELOG section found for {version}", file=sys.stderr)
        return 1

    args.output.write_text(f"{notes}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
