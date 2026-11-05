#!/usr/bin/env python3
"""Probe an LG NetCast 2.0 television that speaks the HDCP protocol.

This tool uses only the Python standard library. It is intended for
troubleshooting and for collecting information before installing the Home
Assistant integration.

Examples:
    python3 tools/probe_hdcp.py --host 192.0.2.10 --pair
    python3 tools/probe_hdcp.py --host 192.0.2.10 --key ABC123
    python3 tools/probe_hdcp.py --host 192.0.2.10 --key ABC123 --send VOLUME_UP
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib import error, request
from xml.etree import ElementTree
from xml.sax.saxutils import escape

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "custom_components" / "lg_netcast_hdcp"),
)

from keys import HDCP_KEY_ALIASES, HDCP_KEYS

XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>'
HEADERS = {"Content-Type": "application/atom+xml"}


def _post(
    host: str, port: int, path: str, body: str, timeout: float
) -> tuple[int, str]:
    """POST an XML body to the TV."""
    url = f"http://{host}:{port}/hdcp/api/{path}"
    req = request.Request(
        url,
        data=body.encode(),
        headers=HEADERS,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except error.HTTPError as err:
        return err.code, err.read().decode("utf-8", errors="replace")
    except (error.URLError, TimeoutError, OSError) as err:
        print(f"Connection error: {err}", file=sys.stderr)
        raise SystemExit(1) from err


def _parse_error(text: str) -> str | None:
    """Return a non-200 HDCP error description, if present."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return "The response is not valid XML"

    code = root.findtext(".//HDCPError")
    detail = root.findtext(".//HDCPErrorDetail") or ""
    if code and code != "200":
        return f"HDCP error {code}: {detail}".strip()
    return None


def _session(text: str) -> str | None:
    """Extract a session ID from an auth response."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return None
    return root.findtext(".//session")


def _auth_body(auth_type: str, value: str | None = None) -> str:
    """Build an auth request body."""
    value_element = f"<value>{escape(value)}</value>" if value else ""
    return f"{XML_DECLARATION}<auth><type>{auth_type}</type>{value_element}</auth>"


def _command_body(session: str, code: str) -> str:
    """Build a command request body."""
    return (
        f"{XML_DECLARATION}<command>"
        f"<session>{escape(session)}</session>"
        "<type>HandleKeyInput</type>"
        f"<value>{code}</value>"
        "</command>"
    )


def _resolve_key(value: str) -> str:
    """Resolve a key name or hexadecimal code."""
    candidate = value.strip().upper()
    if candidate.startswith("0X"):
        candidate = candidate[2:]
    if candidate in HDCP_KEYS:
        return HDCP_KEYS[candidate]
    if candidate in HDCP_KEY_ALIASES:
        return HDCP_KEY_ALIASES[candidate]
    if len(candidate) == 2 and all(char in "0123456789ABCDEF" for char in candidate):
        return candidate
    raise ValueError(f"Unknown key: {value}")


def _print_keys() -> None:
    """Print the supported key names."""
    for name, code in sorted(HDCP_KEYS.items()):
        print(f"{name:20} {code}")
    print("\nAliases:")
    for name, code in sorted(HDCP_KEY_ALIASES.items()):
        print(f"{name:20} {code}")


def main() -> None:
    """Run the probe."""
    parser = argparse.ArgumentParser(
        description="Probe an LG NetCast 2.0 HDCP television."
    )
    parser.add_argument("--host", help="TV IP address or hostname")
    parser.add_argument("--port", type=int, default=8080, help="HDCP HTTP port")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout")
    parser.add_argument(
        "--pair",
        action="store_true",
        help="Ask the TV to display a pairing key",
    )
    parser.add_argument(
        "--key",
        help="Pairing key to exchange for a session",
    )
    parser.add_argument(
        "--send",
        action="append",
        default=[],
        metavar="KEY",
        help="Send a key name or two-digit hex code (repeatable)",
    )
    parser.add_argument(
        "--list-keys",
        action="store_true",
        help="Print the supported key names and exit",
    )
    args = parser.parse_args()

    if args.list_keys:
        _print_keys()
        return

    if not args.host:
        parser.error("--host is required unless --list-keys is used")

    if args.pair:
        status, text = _post(
            args.host,
            args.port,
            "auth",
            _auth_body("AuthKeyReq"),
            args.timeout,
        )
        print(f"HTTP {status}")
        print(text)
        error_message = _parse_error(text)
        if error_message:
            raise SystemExit(error_message)
        print("Check the TV screen for the six-character pairing key.")

    session = None
    if args.key:
        status, text = _post(
            args.host,
            args.port,
            "auth",
            _auth_body("AuthReq", args.key.strip().upper()),
            args.timeout,
        )
        print(f"HTTP {status}")
        print(text)
        error_message = _parse_error(text)
        if error_message:
            raise SystemExit(error_message)
        session = _session(text)
        if not session:
            raise SystemExit("The TV did not return a session.")
        print(f"Session: {session}")

    if args.send:
        if not session:
            parser.error("--send requires --key")
        for key in args.send:
            try:
                code = _resolve_key(key)
            except ValueError as err:
                raise SystemExit(str(err)) from err
            status, text = _post(
                args.host,
                args.port,
                "dtv_wifirc",
                _command_body(session, code),
                args.timeout,
            )
            print(f"{key} -> {code}: HTTP {status}")
            print(text)
            error_message = _parse_error(text)
            if error_message:
                raise SystemExit(error_message)


if __name__ == "__main__":
    main()
