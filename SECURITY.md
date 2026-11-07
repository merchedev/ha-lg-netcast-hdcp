# Security policy

## Supported versions

Security fixes are provided for the latest released version. The current line is
0.7.x.

## Reporting a vulnerability

Please report security issues privately through the repository's **Security**
tab using GitHub Security Advisories. If private reporting is unavailable,
contact the maintainer through GitHub without including a pairing key, session
ID, or other secret.

Do not open a public issue containing:

- a pairing key;
- a session ID;
- a full `.storage/core.config_entries` file;
- Home Assistant backups;
- logs with unredacted TV responses.

## Security model

This integration is local-only:

- It talks to the TV over **HTTP** on TCP port `8080`.
- It does not use LG cloud services.
- It has no runtime Python dependencies outside Home Assistant.
- It does not expose a web server.

The HDCP protocol is not encrypted. The pairing key and session travel over the
local network in clear text. Treat the TV network as trusted.

## Pairing key and session

- The pairing key is stored in the Home Assistant config entry, which is kept in
  `.storage/core.config_entries` and included in Home Assistant backups.
- The session is kept in memory only.
- The integration redacts the pairing key and session from diagnostics and
  internal error strings.
- The probe tool redacts session IDs in its output.
- The session is sent as a query parameter to the TV data endpoint because the
  TV requires it. The integration logs the URL without query parameters.

Do not enable verbose `aiohttp` debug logging in logs you share publicly. Review
diagnostics before posting them.

## Recommended network setup

- Keep the TV and Home Assistant on a trusted LAN or VLAN.
- Do not port-forward the TV's port `8080` to the internet.
- Do not expose the TV directly to an untrusted network.
- Protect Home Assistant backups; they contain the pairing key.
- Use a static IP or DHCP reservation, but do not treat the IP as a secret.

## Service permissions

`lg_netcast_hdcp.process_ir_key` only updates Home Assistant state. It does not
send commands to the TV. Access is controlled by Home Assistant's normal service
permissions.

## Release workflow

The release workflow uses the repository `GITHUB_TOKEN` with `contents: write`
only for the release job. The verification job runs Ruff and the test suite
before publishing.
