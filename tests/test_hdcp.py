"""Tests for the HDCP protocol client."""

from __future__ import annotations

import socket

import aiohttp
import pytest
from aiohttp import web
from custom_components.lg_netcast_hdcp.hdcp import (
    HdcpAuthError,
    HdcpConnectionError,
    HdcpProtocolError,
    LgHdcpClient,
)

pytestmark = pytest.mark.usefixtures("socket_enabled")

PAIRING_KEY = "ABC123"
SESSION = "123456789"
NEW_SESSION = "123456789"


def _response(
    session: str | None = None, error: str = "200", detail: str = "OK"
) -> str:
    session_element = f"<session>{session}</session>" if session else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<envelope>"
        f"<HDCPError>{error}</HDCPError>"
        f"<HDCPErrorDetail>{detail}</HDCPErrorDetail>"
        f"{session_element}"
        "</envelope>"
    )


def _data_response(data: str, session: str = SESSION) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<envelope>"
        "<HDCPError>200</HDCPError>"
        "<HDCPErrorDetail>OK</HDCPErrorDetail>"
        f"<session>{session}</session>"
        f"{data}"
        "</envelope>"
    )


class FakeTv:
    """Small fake HDCP server."""

    def __init__(self) -> None:
        self.pairing_key = PAIRING_KEY
        self.session = SESSION
        self.next_session = NEW_SESSION
        self.commands: list[str] = []
        self.data_requests: list[dict[str, str]] = []
        self.auth_requests = 0
        self.reject_first_command = False
        self.reject_first_data = False
        self.malformed_response = False

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_post("/hdcp/api/auth", self.auth)
        app.router.add_post("/hdcp/api/dtv_wifirc", self.command)
        app.router.add_get("/hdcp/api/data", self.data)
        return app

    async def auth(self, request: web.Request) -> web.Response:
        body = await request.text()
        self.auth_requests += 1

        if "AuthKeyReq" in body:
            return web.Response(text=_response())

        if "AuthReq" in body:
            if self.pairing_key in body:
                return web.Response(text=_response(self.next_session))
            return web.Response(
                text=_response(error="401"),
                status=401,
            )

        return web.Response(text=_response(error="400"), status=400)

    async def command(self, request: web.Request) -> web.Response:
        body = await request.text()
        self.commands.append(body)

        if self.reject_first_command:
            self.reject_first_command = False
            return web.Response(text=_response(error="401"), status=401)

        if self.malformed_response:
            return web.Response(text="<not-xml")

        if self.next_session not in body:
            return web.Response(text=_response(error="401"), status=401)

        return web.Response(text=_response(self.next_session))

    async def data(self, request: web.Request) -> web.Response:
        self.data_requests.append(dict(request.query))

        if self.reject_first_data:
            self.reject_first_data = False
            return web.Response(text=_response(error="401"), status=401)

        if request.query.get("session") != self.next_session:
            return web.Response(text=_response(error="401"), status=401)

        target = request.query.get("target")
        if target == "cur_channel":
            return web.Response(
                text=_data_response(
                    "<data>"
                    "<type>terrestrial</type>"
                    "<major>21</major>"
                    "<minor>65535</minor>"
                    "<sourceIndex>1</sourceIndex>"
                    "<physicalNum>47</physicalNum>"
                    "<name>VEO 7</name>"
                    "</data>"
                )
            )
        if target == "context_ui":
            return web.Response(text=_data_response("<mode>VolCh</mode>"))

        return web.Response(
            text=_response(
                error="400",
                detail=(
                    f"Bad request for session {self.next_session} "
                    f"and key {self.pairing_key}"
                ),
            ),
            status=400,
        )


@pytest.fixture
async def tv(aiohttp_client):
    """Return a running fake TV and a client bound to it."""
    fake = FakeTv()
    test_client = await aiohttp_client(fake.app())
    client = LgHdcpClient(
        test_client.server.host,
        PAIRING_KEY,
        test_client.session,
        port=test_client.server.port,
    )
    yield fake, client
    await client.async_close()


async def test_request_pairing_key(tv) -> None:
    """The pairing request reaches the auth endpoint."""
    fake, client = tv
    await client.async_request_pairing_key()
    assert fake.auth_requests == 1


async def test_authenticate(tv) -> None:
    """A valid pairing key produces a cached session."""
    _, client = tv
    session = await client.async_authenticate()
    assert session == NEW_SESSION
    assert client.session_valid is True


async def test_authenticate_rejects_invalid_key(aiohttp_client) -> None:
    """An invalid pairing key raises an auth error."""
    fake = FakeTv()
    test_client = await aiohttp_client(fake.app())
    client = LgHdcpClient(
        test_client.server.host,
        "WRONG1",
        test_client.session,
        port=test_client.server.port,
    )

    with pytest.raises(HdcpAuthError):
        await client.async_authenticate()


async def test_send_named_and_raw_keys(tv) -> None:
    """Named keys and raw decimal codes are converted correctly."""
    fake, client = tv
    await client.async_send_key("VOLUME_UP")
    await client.async_send_key("03")
    await client.async_send_key("09")
    await client.async_send_key("HDMI1")
    await client.async_send_key("UP")

    assert len(fake.commands) == 5
    assert "<value>02</value>" in fake.commands[0]
    assert "<value>03</value>" in fake.commands[1]
    assert "<value>09</value>" in fake.commands[2]
    assert "<value>206</value>" in fake.commands[3]
    assert "<value>64</value>" in fake.commands[4]


async def test_query_current_channel(tv) -> None:
    """The data endpoint is queried with the cached session."""
    fake, client = tv
    root = await client.async_query_data("cur_channel")

    assert root.findtext(".//data/major") == "21"
    assert root.findtext(".//data/name") == "VEO 7"
    assert fake.data_requests == [{"target": "cur_channel", "session": NEW_SESSION}]


async def test_query_reauthenticates_once(tv) -> None:
    """A rejected data session is renewed and the query is retried."""
    fake, client = tv
    fake.reject_first_data = True

    root = await client.async_query_data("context_ui")

    assert root.findtext(".//mode") == "VolCh"
    assert fake.auth_requests == 2
    assert len(fake.data_requests) == 2


async def test_query_rejects_unsupported_target(tv) -> None:
    """An unsupported data target becomes a protocol error."""
    _, client = tv
    with pytest.raises(HdcpProtocolError):
        await client.async_query_data("volume_info")

    assert client.last_error is not None
    assert NEW_SESSION not in client.last_error
    assert PAIRING_KEY not in client.last_error


async def test_send_key_rejects_unknown_key(tv) -> None:
    """Unknown key names and malformed codes are rejected."""
    _, client = tv
    with pytest.raises(ValueError, match="Unsupported remote key"):
        await client.async_send_key("NOT_A_KEY")
    with pytest.raises(ValueError, match="Unsupported remote key"):
        await client.async_send_key("123")
    with pytest.raises(ValueError, match="Unsupported remote key"):
        await client.async_send_key("1A")


async def test_send_key_reauthenticates_once(tv) -> None:
    """A rejected session is renewed and the command is retried."""
    fake, client = tv
    fake.reject_first_command = True

    await client.async_send_key("VOLUME_UP")

    assert len(fake.commands) == 2
    assert fake.auth_requests == 2


async def test_malformed_response(tv) -> None:
    """A non-XML response becomes a protocol error."""
    fake, client = tv
    fake.malformed_response = True

    with pytest.raises(HdcpProtocolError):
        await client.async_send_key("VOLUME_UP")


async def test_connection_error() -> None:
    """A closed port becomes a connection error."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    async with aiohttp.ClientSession() as session:
        client = LgHdcpClient(
            "127.0.0.1",
            PAIRING_KEY,
            session,
            port=port,
        )
        with pytest.raises(HdcpConnectionError):
            await client.async_authenticate()
