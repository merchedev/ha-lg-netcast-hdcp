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

Tested on:

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

## Features

- Turn off the TV.
- Volume up/down and mute.
- Play, pause, and stop.
- Tune to a channel by number.
- Send any supported remote key through a `remote` entity.
- Automatic session reauthentication after the TV wakes up.
- Reauthentication and reconfiguration flows.
- Redacted diagnostics.
- A standalone probe tool for troubleshooting.

## Limitations

- **Power on is not possible over this protocol.** The HTTP server stops when
  the TV enters standby. Use IR, Wake-on-LAN, HDMI-CEC, or RS-232C.
- Power and volume state are assumed. The TV does not expose reliable state
  through this API.
- App launching and direct HDMI input selection are not available. You can send
  key sequences such as `INPUT`, `UP`, `DOWN`, and `OK`.
- One pairing key is stored per TV. A factory reset changes the key.

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
4. Enter the TV's IP address.
5. The TV displays a six-character pairing key.
6. Enter that key in Home Assistant.
7. The integration creates a media player and a remote entity.

The pairing key is stored in the config entry. The session is kept in memory and
is renewed automatically when needed. Some firmware may invalidate the pairing
key after standby or a factory reset; in that case Home Assistant starts the
reauthentication flow and asks for the new key shown on screen.

## Power on

The integration fires a `lg_netcast_hdcp.turn_on` device trigger whenever
something requests the TV to turn on. Create an automation that performs the
actual power-on action.

### Wake-on-LAN example

```yaml
alias: Turn on the LG TV with Wake-on-LAN
triggers:
  - trigger: lg_netcast_hdcp.turn_on
    entity_id: media_player.lg_tv
actions:
  - action: wake_on_lan.send_magic_packet
    data:
      mac: "AA:BB:CC:DD:EE:FF"
```

Wake-on-LAN must be supported and enabled by the TV. Many 2011 models do not
support it.

### IR example

Create a script that sends the LG power command through your IR blaster, then
call it from the trigger:

```yaml
alias: Turn on the LG TV with IR
triggers:
  - trigger: lg_netcast_hdcp.turn_on
    entity_id: media_player.lg_tv
actions:
  - action: script.turn_on_lg_tv_ir
```

The LG IR protocol is NEC. You can learn the original remote's power button with
Broadlink, ESPHome, or another IR blaster.

### HDMI-CEC and RS-232C

- HDMI-CEC: use the `hdmi_cec` integration if Home Assistant is connected to the
  TV through a CEC-capable adapter.
- RS-232C: the 42LW650S has an RS-232C port. LG's serial protocol supports power
  on (`ka 01 01`), power off (`ka 01 00`), volume, and input selection.

## Entities

### `media_player`

- `turn_off`
- `volume_up` / `volume_down`
- `volume_mute`
- `media_play` / `media_pause` / `media_stop`
- `play_media` with `media_content_type: channel`

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

Expected. The HDCP HTTP server stops in standby. Configure an external power-on
action as described above.

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
