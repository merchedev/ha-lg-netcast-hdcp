# AGENTS.md

## Mission

Build a small, reliable Home Assistant custom integration for LG NetCast 2.0
(2011) televisions that expose the HDCP HTTP remote-control protocol on port
8080. The integration must stay local-only and must not depend on LG cloud
services.

The integration is intentionally separate from the official `lg_netcast`
integration, which supports NetCast 3.0/4.0 (2012-2013).

## Non-negotiable rules

- Work only on the `AI-Developer` branch. Do not commit directly to `main`.
- Commit subjects must start with `AI:`. Example:
  `AI: add HDCP session reauthentication`.
- All code, comments, documentation, tests, and commit messages are in English.
- Keep changes focused. Do not refactor unrelated code.
- Update tests and documentation together with behavior changes.
- Never log, expose, or commit a pairing key or a session ID.
- Never add a runtime dependency without documenting why.
- Use async code. Never perform blocking I/O in the event loop.
- Prefer Home Assistant helpers and standard patterns over custom plumbing.
- Do not copy LG source code, assets, or proprietary documentation. Implement
  from publicly documented/observed protocol behavior.

## Protocol invariants

The following behavior was verified against an LG 42LW650S-ZC (NetCast 2.0,
firmware 0001.0009):

- Protocol: HDCP over HTTP on TCP port 8080.
- Auth endpoint: `POST /hdcp/api/auth`.
- Command endpoint: `POST /hdcp/api/dtv_wifirc`.
- Pairing request body:
  `<?xml version="1.0" encoding="utf-8"?><auth><type>AuthKeyReq</type></auth>`
- Pairing response body is an `<envelope>` with `HDCPError` set to `200`.
  The television displays a six-character pairing key.
- Session request body:
  `<?xml version="1.0" encoding="utf-8"?><auth><type>AuthReq</type><value>KEY</value></auth>`
- Session response contains `<session>...</session>`.
- Command body:
  `<?xml version="1.0" encoding="utf-8"?><command><session>SESSION</session><type>HandleKeyInput</type><value>CODE</value></command>`
- Key codes are two-digit hexadecimal strings. `VOLUME_UP` is `02`, not `24`
  (decimal `24` belongs to the newer ROAP protocol).
- The session becomes invalid when the television enters standby. Re-run
  `AuthReq` with the stored pairing key after the television is powered on.
- Some firmware may invalidate the pairing key after standby or a factory
  reset. The reauthentication flow must handle a rejected key by requesting a
  new `AuthKeyReq`.
- The television cannot be powered on over this protocol because the HTTP
  server stops in standby. Power-on must use IR, Wake-on-LAN, HDMI-CEC, or
  RS-232C.

## Architecture

- `hdcp.py`: protocol client. Owns HTTP, XML parsing, pairing, session
  lifecycle, one automatic reauthentication retry, and key-code validation.
- `config_flow.py`: manual host setup, pairing, reauthentication,
  reconfiguration, and options for power-on behavior and input sequences.
- `media_player.py`: TV entity. Power off, volume, mute, playback, channel
  tuning, configured input sources, and conditional power-on.
- `button.py`: remote-key buttons for common navigation, input, channel, and
  digit keys.
- `remote.py`: generic key sender. Accepts names such as `VOLUME_UP` and raw
  two-digit hexadecimal codes.
- `wol.py`: Wake-on-LAN magic packet helper.
- `profiles.py`: model/protocol profiles and key maps. Adding a model should
  mean adding a profile, not changing integration logic.
- `diagnostics.py`: redacted diagnostics. Pairing keys and sessions must never
  appear in the output.

## Home Assistant conventions

- Use `ConfigEntry` runtime data.
- Use `async_get_clientsession(hass)`; do not create a client session per
  request.
- Use an options flow for power-on behavior and input-source mappings.
- Expose `TURN_ON` only when the user configured Wake-on-LAN or a custom action.
- Never hardcode a user's MAC address, input names, input order, or IR action.
- Use `assumed_state = True` because the TV does not report reliable power or
  volume state.
- Keep config-entry data limited to host and pairing key. Sessions live in
  memory only.
- Use translations for every user-facing config-flow string.

## Definition of done

Before committing:

```bash
ruff check .
ruff format --check .
pytest
```

A change is complete only when:

- tests cover the new behavior,
- user-visible behavior is documented in `README.md` or `docs/`,
- pairing keys and session IDs are redacted from logs and diagnostics,
- `hassfest` and HACS validation pass in CI,
- the change has been manually verified against a real TV when it touches the
  protocol layer.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt ruff
pytest
ruff check .
ruff format --check .
```

## Release process

1. Verify on a real TV.
2. Update `custom_components/lg_netcast_hdcp/manifest.json` version.
3. Update `README.md` and `CHANGELOG.md`.
4. Commit with `AI: release vX.Y.Z`.
5. Tag `vX.Y.Z`.
6. Publish a GitHub release so HACS can offer the version.
