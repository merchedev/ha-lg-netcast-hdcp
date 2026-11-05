# LG NetCast 2.0 HDCP protocol

This document describes the local HTTP protocol used by LG NetCast 2.0
televisions from 2011. It was verified against an LG 42LW650S-ZC running
firmware 0001.0009.

The protocol is unofficial. LG does not document it as a public API. Treat it as
best-effort and keep changes covered by tests.

## Transport

- TCP port: `8080`
- Scheme: HTTP (not HTTPS)
- Content type: `application/atom+xml`
- Server header: `LG HDCP Server`
- Server behavior: closes the connection after each response

The server is only available while the television is powered on. It disappears
in standby, so it cannot be used to power the TV on.

## Pairing

### 1. Request a pairing key

```http
POST /hdcp/api/auth
Content-Type: application/atom+xml

<?xml version="1.0" encoding="utf-8"?><auth><type>AuthKeyReq</type></auth>
```

The television displays a six-character key. The response is:

```xml
<?xml version="1.0" encoding="utf-8"?>
<envelope>
  <HDCPError>200</HDCPError>
  <HDCPErrorDetail>OK</HDCPErrorDetail>
</envelope>
```

### 2. Exchange the key for a session

```http
POST /hdcp/api/auth
Content-Type: application/atom+xml

<?xml version="1.0" encoding="utf-8"?><auth><type>AuthReq</type><value>ABC123</value></auth>
```

Successful response:

```xml
<?xml version="1.0" encoding="utf-8"?>
<envelope>
  <HDCPError>200</HDCPError>
  <HDCPErrorDetail>OK</HDCPErrorDetail>
  <session>123456789</session>
</envelope>
```

The pairing key normally survives power cycles and is only expected to change
after a factory reset. Some firmware revisions invalidate it after standby;
in that case request a fresh key with `AuthKeyReq`. The session is always
invalidated when the television enters standby. Request a new session with the
stored pairing key after power-on.

## Commands

```http
POST /hdcp/api/dtv_wifirc
Content-Type: application/atom+xml

<?xml version="1.0" encoding="utf-8"?><command><session>123456789</session><type>HandleKeyInput</type><value>02</value></command>
```

`02` is `VOLUME_UP` in the 2011 HDCP key map. Do not use the ROAP decimal code
`24`; that belongs to the 2012+ protocol and is ignored by these televisions.

A successful response echoes the session:

```xml
<?xml version="1.0" encoding="utf-8"?>
<envelope>
  <HDCPError>200</HDCPError>
  <HDCPErrorDetail>OK</HDCPErrorDetail>
  <session>123456789</session>
</envelope>
```

A `200 OK` only means the request was accepted. The TV does not report whether a
particular key was handled.

## Key codes

| Name | Code |
|---|---|
| POWER | `08` |
| VOLUME_UP | `02` |
| VOLUME_DOWN | `03` |
| MUTE | `09` |
| CHANNEL_UP | `00` |
| CHANNEL_DOWN | `01` |
| INPUT | `0B` |
| UP | `40` |
| DOWN | `41` |
| LEFT | `07` |
| RIGHT | `06` |
| OK | `44` |
| BACK | `28` |
| EXIT | `5B` |
| MENU | `43` |
| HOME | `23` |
| NETCAST | `59` |
| GUIDE | `A9` |
| INFO | `AA` |
| PLAY | `B0` |
| PAUSE | `BA` |
| STOP | `B1` |
| REWIND | `8F` |
| FAST_FORWARD | `8E` |
| RECORD | `BD` |
| RED | `72` |
| GREEN | `71` |
| YELLOW | `63` |
| BLUE | `61` |
| NUMBER_0 … NUMBER_9 | `10` … `19` |

The complete map lives in
`custom_components/lg_netcast_hdcp/keys.py`.

## Error handling

- `HDCPError` other than `200` indicates a rejected request.
- `401`/`403` or `Unauthorized` means the session is no longer valid. Request a
  new session with the stored pairing key.
- A connection error usually means the TV is off, on a different network, or
  port 8080 is blocked.
- Malformed XML means the request reached something other than the HDCP server.

## Power-on limitation

The HTTP server is part of the TV's running software and is not available in
standby. Power-on requires one of:

- IR (NEC LG codes),
- Wake-on-LAN, if supported by the model,
- HDMI-CEC,
- RS-232C (`ka 01 01` on the 42LW650S).

The integration exposes a `lg_netcast_hdcp.turn_on` device trigger so users can
run the appropriate external action.

## References

- `lgcommander` by melka: original 2011 HDCP pairing and command flow.
- `service.lgtv.remote` key codes: HDCP hexadecimal key table.
- Home Assistant community thread "Support for pre 2012 models LG Netcast TV's
  needed".
- LG UDAP documentation for the related 2012+ protocol.
