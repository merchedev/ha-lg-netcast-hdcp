# LG NetCast HDCP for Home Assistant

Local Home Assistant integration for LG NetCast 2.0 televisions (2011) that use
the HDCP remote-control protocol on TCP port 8080.

This is an unofficial, community-maintained integration. It is not affiliated
with LG Electronics.

## Why this exists

Home Assistant's official `lg_netcast` integration supports NetCast 3.0 and
4.0 (2012-2013). LG's 2011 NetCast 2.0 televisions use a different protocol:
the "LG HDCP Server" exposed on port 8080. Those televisions are left out of the
official integration, even though they can be controlled locally after a
six-character pairing step.

This integration fills that gap.

## Supported televisions

Developed and paired against:

- LG 42LW650S-ZC (2011), NetCast 2.0, firmware 0001.0009.

Likely compatible with other 2011 LW/LV-series NetCast 2.0 televisions. To
check, run:

```bash
curl -i -X POST \
  -H 'Content-Type: application/atom+xml' \
  --data '<?xml version="1.0" encoding="utf-8"?><auth><type>AuthKeyReq</type></auth>' \
  http://TV_IP:8080/hdcp/api/auth
```

If the response contains `Server: LG HDCP Server` and the TV displays a
six-character pairing key, this integration should work.

Do not use this integration for 2012-2013 NetCast 3.0/4.0 televisions. Use the
official `lg_netcast` integration instead.

### Model profiles

Protocol details and key maps live in `profiles.py`. The initial profile is
`hdcp_2011`. Adding support for another model should mean adding a profile, not
changing the integration logic. Input names, power-on methods, MAC addresses,
and IR actions are user configuration and are never hardcoded.

## Features

- Turn off the TV.
- Volume up/down and mute.
- Play, pause, and stop.
- Tune to a channel by number.
- Buttons for Home, Back, OK, Input, navigation, channels, and digits.
- Configurable input-source key sequences.
- Optional Wake-on-LAN or custom-action power-on.
- Send any supported remote key through a `remote` entity.
- Automatic session reauthentication after the TV wakes up.
- Reauthentication and reconfiguration flows.
- Redacted diagnostics.
- A standalone probe tool for troubleshooting.

## Limitations

- **Power on is not possible over this protocol.** The HTTP server stops when
  the TV enters standby. Configure Wake-on-LAN or a custom action (IR, CEC, or
  RS-232C). If no method is configured, the turn-on feature is hidden.
- Power and volume state are assumed. The TV does not expose reliable state
  through this API.
- Direct input selection is not exposed by the protocol. Input sources are
  configured by the user as key sequences because the available inputs and the
  number of navigation presses vary by installation. The `INPUT`, arrow, and
  `OK` buttons are always available as a fallback.
- One pairing key is stored per TV. A factory reset changes the key.
- Some firmware revisions invalidate the pairing key after standby. If yours
  does this on every power cycle, the HDCP network protocol is not practical
  for daily control; use IR or RS-232C for power and, if possible, keep the TV
  on the network for the rest of the controls.

## Installation

### HACS (recommended)

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add `https://github.com/merchedev/ha-lg-netcast-hdcp` as an **Integration**.
5. Install **LG NetCast HDCP**.
6. Restart Home Assistant.

### Manual installation

Copy `custom_components/lg_netcast_hdcp` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

## Configuration

1. Make sure the TV is on and connected to the same network as Home Assistant.
2. In Home Assistant, go to **Settings → Devices & services → Add integration**.
3. Search for **LG NetCast HDCP**.
4. Enter the TV's IP address. Use a static IP or a DHCP reservation in your
   router; if the TV's IP changes, the integration loses the connection.
5. The TV displays a six-character pairing key.
6. Enter that key in Home Assistant.
7. The integration creates a media player, a remote entity, and remote-key
   buttons.

The pairing key is stored in the config entry. The session is kept in memory and
is renewed automatically when needed. Some firmware may invalidate the pairing
key after standby or a factory reset; in that case Home Assistant starts the
reauthentication flow and asks for the new key shown on screen.

After setup, open the integration's **Configure** dialog to choose the power-on
method and, optionally, define input sources.

## Power on

Power-on is configured in **Settings → Devices & services → LG NetCast HDCP →
Configure**. Choose one of:

- **None**: the turn-on feature is hidden. Turn-off still works over NetCast.
- **Wake-on-LAN**: enter the TV's Ethernet MAC address, broadcast address, and
  port. The integration sends a magic packet when `turn_on` is requested.
- **Custom action**: select an existing Home Assistant action. This can be an
  ESPHome IR service, a `remote.send_command`, an HDMI-CEC action, an RS-232C
  script, or any other action. **An IR integration must already be configured
  and working before selecting this option.**
- **Both**: send Wake-on-LAN and then run the custom action.

If no method is configured, no turn-on button is shown. Apagar always uses the
NetCast HDCP protocol.

Wake-on-LAN must be supported and enabled by the TV. Many 2011 models do not
support it; in that case use the custom-action/IR route.

### Input sources

The HDCP protocol only exposes the `INPUT` key, not a command for a specific
HDMI port. Available inputs and menu order vary between installations, and
disconnected inputs may be disabled. Configure input sources in the same
**Configure** dialog as a mapping of names to key sequences:

```yaml
input_sources:
  HDMI1:
    - INPUT
    - DOWN
    - OK
  HDMI2:
    - INPUT
    - DOWN
    - DOWN
    - OK
```

Names and sequences are user-defined. When configured, the media player exposes
a source selector. If no sources are configured, the `INPUT`, arrow, and `OK`
buttons remain available.

### HDMI-CEC and RS-232C

- HDMI-CEC: use the `hdmi_cec` integration if Home Assistant is connected to the
  TV through a CEC-capable adapter. Select that action as the custom turn-on
  action.
- RS-232C: the 42LW650S has an RS-232C port. LG's serial protocol supports power
  on (`ka 01 01`), power off (`ka 01 00`), volume, and input selection. Expose
  it through a script or another integration and select that action.

## Entities

### `media_player`

- `turn_off`
- `volume_up` / `volume_down`
- `volume_mute`
- `media_play` / `media_pause` / `media_stop`
- `play_media` with `media_content_type: channel`
- `select_source` for user-configured input sequences

### `button`

Buttons are created for:

`Home`, `Back`, `OK`, `Input`, `Up`, `Down`, `Left`, `Right`,
`Channel up`, `Channel down`, and digits `0`–`9`.

### `remote`

The remote entity accepts key names and raw hexadecimal codes:

```yaml
action: remote.send_command
target:
  entity_id: remote.lg_tv_remote
data:
  command:
    - HOME
    - DOWN
    - OK
```

Supported names include:

`POWER`, `VOLUME_UP`, `VOLUME_DOWN`, `MUTE`, `CHANNEL_UP`, `CHANNEL_DOWN`,
`UP`, `DOWN`, `LEFT`, `RIGHT`, `OK`, `BACK`, `EXIT`, `MENU`, `HOME`, `INPUT`,
`NETCAST`, `GUIDE`, `INFO`, `PLAY`, `PAUSE`, `STOP`, `REWIND`,
`FAST_FORWARD`, `RECORD`, `RED`, `GREEN`, `YELLOW`, `BLUE`, and `NUMBER_0`
through `NUMBER_9`.

Raw codes are two hexadecimal digits, for example `02` for volume up.

## Reauthentication

The TV invalidates the session when it enters standby. The integration
automatically requests a new session with the stored pairing key when a command
is sent after the TV wakes up.

If the TV no longer accepts the pairing key, Home Assistant starts a
reauthentication flow. Turn the TV on, let it finish booting, and enter the new
six-character key shown on screen.

## Troubleshooting

### The TV does not show a pairing key

- Make sure the TV is on and on the Home screen.
- Check that Home Assistant and the TV are on the same network.
- Check that TCP port 8080 is reachable.
- Run the probe tool:

```bash
python3 tools/probe_hdcp.py --host TV_IP --pair
```

### `Unauthorized`

- The session expired. The integration should renew it automatically.
- If the pairing key was rejected, start the reauthentication flow.
- Wait 15-30 seconds after powering on before retrying; the HTTP server may not
  be ready yet.

### The TV turns off but does not turn on

Expected. The HDCP HTTP server stops in standby. Configure Wake-on-LAN or a
custom action in the integration options. If neither is configured, the turn-on
feature is intentionally hidden.

### Input selection does nothing

The input menu has to be open and the key sequence must match your TV's current
input layout. Disconnected inputs are often disabled, so the number of
`DOWN`/`UP` presses changes. Adjust `input_sources` with the `remote` entity or
the `INPUT`/arrow/`OK` buttons, then update the sequence.

### Volume commands return `200 OK` but nothing happens

The command endpoint returns `200` for accepted requests even when a key is not
handled. Make sure you are using the HDCP hexadecimal codes (`02`, `03`), not
the ROAP decimal codes (`24`, `25`).

## Debug logging

```yaml
logger:
  logs:
    custom_components.lg_netcast_hdcp: debug
```

Pairing keys and session IDs are never logged.

## Protocol documentation

See [docs/protocol.md](docs/protocol.md) for endpoints, XML payloads, key codes,
and session behavior.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt ruff
pytest
ruff check .
ruff format --check .
```

The repository is developed on the `AI-Developer` branch. Commit subjects start
with `AI:`. See [AGENTS.md](AGENTS.md).

## License

MIT. See [LICENSE](LICENSE).

LG and NetCast are trademarks of LG Electronics. This project is unofficial and
is not endorsed by LG.
