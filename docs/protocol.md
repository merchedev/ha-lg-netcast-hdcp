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

## State queries

While the TV is on, the 2011 firmware also exposes a data endpoint. The session
from `AuthReq` is passed as a query parameter:

```http
GET /hdcp/api/data?target=cur_channel&session=123456789
GET /hdcp/api/data?target=context_ui&session=123456789
```

Without a session the endpoint returns `401 Unauthorized`. The
`dtv_wifirc` endpoint is POST-only; a GET query against it returns `406 Not
Acceptable`.

A valid current channel response looks like:

```xml
<?xml version="1.0" encoding="utf-8"?>
<envelope>
  <HDCPError>200</HDCPError>
  <HDCPErrorDetail>OK</HDCPErrorDetail>
  <session>123456789</session>
  <data>
    <type>terrestrial</type>
    <major>21</major>
    <minor>65535</minor>
    <sourceIndex>1</sourceIndex>
    <physicalNum>47</physicalNum>
    <name>VEO 7</name>
  </data>
</envelope>
```

`minor=65535` means there is no subchannel. On an external input or in some UI
states the response contains sentinel values instead:

```xml
<data>
  <type>satellite</type>
  <major>16368</major>
  <minor>65535</minor>
  <sourceIndex>9</sourceIndex>
  <physicalNum>65535</physicalNum>
  <name></name>
</data>
```

The sentinel values were identical for HDMI1 and HDMI4, so they identify an
external input but not a specific HDMI port.

`context_ui` returns the current UI mode:

```xml
<envelope>
  <HDCPError>200</HDCPError>
  <HDCPErrorDetail>OK</HDCPErrorDetail>
  <session>123456789</session>
  <mode>VolCh</mode>
</envelope>
```

Observed modes on the tested model include `VolCh` for normal TV/HDMI viewing
and `TouchPad` for the Home and guide overlays. `model_info` and `version_info`
also work. `volume_info` returns `400 Bad Request` on this firmware and is not
used.

## Key codes

The television parses the value as a **decimal number** and stops at the first
non-digit character. The integration's raw-code input accepts two-digit decimal
strings from `00` to `99`; letter suffixes are not valid separate codes.

The tested model also accepts the following confirmed direct-input and vertical
navigation codes. Use the named keys; the integration intentionally does not
accept arbitrary three-digit raw codes.

| Name | Code |
|---|---|
| POWER | `08` |
| VOLUME_UP | `02` |
| VOLUME_DOWN | `03` |
| MUTE | `09` |
| CHANNEL_UP | `00` |
| CHANNEL_DOWN | `01` |
| LEFT | `07` |
| RIGHT | `06` |
| UP | `64` |
| DOWN | `65` |
| INPUT | `11` |
| Q_MENU | `10` |
| TIMER | `14` |
| TV_RADIO | `15` |
| OK | `68` |
| EXIT | `40` |
| HOME | `67` |
| HDMI1 | `206` |
| HDMI2 | `204` |
| HDMI3 | `233` |
| HDMI4 | `218` |
| NUMBER_0 … NUMBER_9 | `16`–`19`, `20`–`25` |
| BLUE | `97` |
| YELLOW | `99` |

The complete tested matrix, including unknown codes, is in
[`docs/keycodes.md`](keycodes.md). The integration map lives in
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
- Wake-on-LAN, if supported by the model. The tested 42LW650S-ZC (firmware
  0001.0009) did **not** wake with a magic packet, so Wake-on-LAN support
  cannot be assumed for 2011 models,
- HDMI-CEC,
- RS-232C (`ka 01 01` on the 42LW650S).

The integration lets the user configure a Wake-on-LAN packet or a custom Home
Assistant action (IR, CEC, RS-232C, or a script) for power-on. If neither is
configured, the turn-on feature is hidden. Wake-on-LAN remains available for
models where it is known to work.

## References

- `lgcommander` by melka: original 2011 HDCP pairing and command flow.
- Home Assistant community thread "Support for pre 2012 models LG Netcast TV's
  needed".
- LG UDAP documentation for the related 2012+ protocol.
