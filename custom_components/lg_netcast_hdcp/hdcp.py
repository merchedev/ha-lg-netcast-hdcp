"""Async client for the LG NetCast HDCP HTTP protocol."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Final
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import aiohttp

from .const import (
    AUTH_PATH,
    COMMAND_PATH,
    DATA_PATH,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    HDCP_ERROR,
    HDCP_ERROR_DETAIL,
    HDCP_ERROR_OK,
    HDCP_KEY_ALIASES,
    HDCP_SESSION,
    RAW_KEY_PATTERN,
)
from .profiles import DEFAULT_PROFILE, TvProfile

_LOGGER = logging.getLogger(__name__)

_HEADERS: Final = {"Content-Type": "application/atom+xml"}
_XML_DECLARATION: Final = '<?xml version="1.0" encoding="utf-8"?>'
_RAW_KEY_PATTERN: Final = re.compile(RAW_KEY_PATTERN)
_AUTH_ERROR_CODES: Final = {"401", "403"}


class HdcpError(Exception):
    """Base error for the HDCP client."""


class HdcpConnectionError(HdcpError):
    """Raised when the TV cannot be reached."""


class HdcpProtocolError(HdcpError):
    """Raised when the TV returns an unexpected protocol response."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """Initialize the error."""
        super().__init__(message)
        self.code = code


class HdcpAuthError(HdcpError):
    """Raised when pairing fails or the session is rejected."""


class LgHdcpClient:
    """Client for the HDCP API exposed by NetCast 2.0 televisions."""

    def __init__(
        self,
        host: str,
        pairing_key: str,
        session: aiohttp.ClientSession,
        *,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        profile: TvProfile = DEFAULT_PROFILE,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.pairing_key = pairing_key
        self.profile = profile
        self.last_error: str | None = None
        self._session = session
        self._port = port
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session_id: str | None = None
        self._lock = asyncio.Lock()

    @property
    def session_valid(self) -> bool:
        """Return whether a session is cached."""
        return self._session_id is not None

    async def async_request_pairing_key(self) -> None:
        """Ask the TV to display a new pairing key."""
        await self._post(AUTH_PATH, self._auth_body("AuthKeyReq"))

    async def async_authenticate(self) -> str:
        """Request a session using the stored pairing key."""
        async with self._lock:
            return await self._async_authenticate_locked()

    async def async_send_key(self, key: str) -> None:
        """Send a remote key to the TV."""
        code = self._resolve_key(key)

        async with self._lock:
            if self._session_id is None:
                await self._async_authenticate_locked()

            try:
                await self._async_send_code_locked(code)
            except HdcpAuthError:
                self._session_id = None
                await self._async_authenticate_locked()
                await self._async_send_code_locked(code)

    async def async_send_sequence(self, keys: list[str], *, delay: float = 0.2) -> None:
        """Send a sequence of keys, pausing between them."""
        for index, key in enumerate(keys):
            await self.async_send_key(key)
            if index < len(keys) - 1:
                await asyncio.sleep(delay)

    async def async_query_data(self, target: str) -> ElementTree.Element:
        """Query a data target using the cached session."""
        async with self._lock:
            if self._session_id is None:
                await self._async_authenticate_locked()

            try:
                return await self._async_query_data_locked(target)
            except HdcpAuthError:
                self._session_id = None
                await self._async_authenticate_locked()
                return await self._async_query_data_locked(target)

    async def async_close(self) -> None:
        """Drop the cached session.

        The Home Assistant shared client session is owned by Home Assistant and
        must not be closed here.
        """
        self._session_id = None

    async def _async_authenticate_locked(self) -> str:
        """Request a session while the lock is held."""
        if not self.pairing_key:
            raise HdcpAuthError("A pairing key is required")

        root = await self._post(AUTH_PATH, self._auth_body("AuthReq", self.pairing_key))
        session_id = root.findtext(f".//{HDCP_SESSION}")

        if not session_id:
            raise HdcpAuthError("The TV did not return a session")

        self._session_id = session_id
        return session_id

    async def _async_send_code_locked(self, code: str) -> None:
        """Send a key code while the lock is held."""
        if self._session_id is None:
            raise HdcpAuthError("No active session")

        body = (
            f"{_XML_DECLARATION}<command>"
            f"<session>{escape(self._session_id)}</session>"
            "<type>HandleKeyInput</type>"
            f"<value>{code}</value>"
            "</command>"
        )
        await self._post(COMMAND_PATH, body)

    async def _async_query_data_locked(self, target: str) -> ElementTree.Element:
        """Query a data target while the lock is held."""
        if self._session_id is None:
            raise HdcpAuthError("No active session")

        return await self._request(
            "GET",
            DATA_PATH,
            params={"target": target, "session": self._session_id},
        )

    async def _post(self, path: str, body: str) -> ElementTree.Element:
        """POST an XML body and return the parsed envelope."""
        return await self._request("POST", path, body=body)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: str | None = None,
        params: dict[str, str] | None = None,
    ) -> ElementTree.Element:
        """Send an HTTP request and return the parsed envelope."""
        url = f"http://{self.host}:{self._port}/hdcp/api/{path}"
        _LOGGER.debug("Sending HDCP request to %s", url)

        try:
            async with self._session.request(
                method,
                url,
                data=body.encode() if body is not None else None,
                params=params,
                headers=_HEADERS,
                timeout=self._timeout,
            ) as response:
                text = await response.text()
                status = response.status
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            self.last_error = self._redact_secrets(str(err))
            raise HdcpConnectionError(f"Could not reach {self.host}") from err

        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError as err:
            self.last_error = "Malformed response"
            raise HdcpProtocolError("The TV returned malformed XML") from err

        error_code = root.findtext(f".//{HDCP_ERROR}")
        detail = root.findtext(f".//{HDCP_ERROR_DETAIL}") or ""

        if error_code and error_code != HDCP_ERROR_OK:
            self.last_error = self._redact_secrets(detail or f"HDCP error {error_code}")
            if error_code in _AUTH_ERROR_CODES or "unauthorized" in detail.lower():
                raise HdcpAuthError(self.last_error)
            raise HdcpProtocolError(self.last_error, code=error_code)

        if status != 200:
            self.last_error = f"HTTP {status}"
            raise HdcpConnectionError(f"HTTP {status} from {self.host}")

        self.last_error = None
        return root

    @staticmethod
    def _auth_body(auth_type: str, value: str | None = None) -> str:
        """Build an authentication request body."""
        value_element = f"<value>{escape(value)}</value>" if value else ""
        return f"{_XML_DECLARATION}<auth><type>{auth_type}</type>{value_element}</auth>"

    def _redact_secrets(self, value: str) -> str:
        """Remove cached secrets from an error string."""
        if self.pairing_key and self.pairing_key in value:
            value = value.replace(self.pairing_key, "REDACTED")
        if self._session_id and self._session_id in value:
            value = value.replace(self._session_id, "REDACTED")
        return value

    def _resolve_key(self, key: str) -> str:
        """Resolve a named key or a two-digit decimal code."""
        candidate = str(key).strip().upper()

        if candidate in self.profile.keys:
            return self.profile.keys[candidate]
        if candidate in HDCP_KEY_ALIASES:
            return HDCP_KEY_ALIASES[candidate]
        if _RAW_KEY_PATTERN.fullmatch(candidate):
            return candidate

        raise ValueError(
            "Unsupported remote key; use a key name or a decimal code from 00 to 99"
        )
