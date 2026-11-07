# LG NetCast HDCP for Home Assistant

Local Home Assistant integration for LG NetCast 2.0 televisions (2011) that use
the HDCP remote-control protocol on TCP port 8080.

This is an unofficial, community-maintained integration. It is not affiliated
with LG Electronics.

## Why this exists

Home Assistant's official `lg_netcast` integration supports NetCast 3.0 and 4.0
(2012–2013). LG's 2011 NetCast 2.0 televisions use a different protocol: the
"LG HDCP Server" exposed on port 8080. Those televisions are left out of the
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

Do not use this integration for 2012–2013 NetCast 3.0/4.0 televisions. Use the
official `lg_netcast` integration instead.

## Installation

### HACS

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add `https://github.com/merchedev/ha-lg-netcast-hdcp` as an **Integration**.
5. Install **LG NetCast HDCP**.
6. Restart Home Assistant.

### Manual

Copy `custom_components/lg_netcast_hdcp` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

After an update through HACS, restart Home Assistant before configuring the new
options.

## Quick start

1. Install the integration through HACS or manually.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **LG NetCast HDCP**.
5. Enter the TV IP address. Use a static IP or DHCP reservation.
6. Enter the six-character pairing key shown on the TV.
7. Open the integration's **Configure** dialog, choose **Power-on behavior**, and
   select your power-on method.

Expected result: a media player, a remote entity, and remote-key buttons are
created. The media player reads power, channel, channel name, and UI mode while
the TV is on.

## Choose your setup

| Goal | What you need |
|---|---|
| Control the TV while it is on | Install and pair |
| Turn the TV on | IR, HDMI-CEC, Wake-on-LAN, or RS-232C |
| Use an Apple TV as the power-on source | HDMI-CEC + **Source before power off** |
| Know which HDMI input is active after using the TV remote | IR receiver |
| Show the channel on a dashboard | Media-control card or an attribute card |
| Use a normal TV remote to track mute | IR receiver |
| Select HDMI1–HDMI4 or AV1 | No mapping needed; they are in the source selector |
| Use a custom source name or non-direct input | `input_sources` |

You do **not** need an IR receiver for power, channel, or UI mode. It is optional.

## Features

- Turn off the TV, control volume, mute, and tune to a channel by number.
- Poll power, channel, channel name, and UI mode from the HDCP data endpoint.
- Direct input keys for HDMI1–HDMI4 and AV1, available automatically in the
  source selector.
- Buttons for Home, OK, Input, HDMI1–HDMI4, Left/Right/Up/Down, channels,
  Q.Menu, Timer, TV/Radio, Exit, and digits.
- Configurable input-source sequences for custom or non-direct inputs and IR
  tracking.
- Optional Wake-on-LAN or custom-action power-on.
- Optional source-before-power-off for HDMI-CEC wake compatibility.
- Optional external IR receiver state tracking.
- Sectioned options for power-on behavior, input sources, and state tracking.
- English and Spanish user-interface translations.
- Visible command errors and automatic reauthentication after the TV wakes up.
- Redacted diagnostics.
- A standalone probe tool for troubleshooting.

## Limitations

- **Power on is not possible over this protocol.** The HTTP server stops in
  standby. Use IR, HDMI-CEC, Wake-on-LAN, or RS-232C.
- **The active HDMI input and volume are not reported.** On external inputs the
  channel response is invalid, so the integration knows “external input” but not
  which HDMI port. Without IR, input changes made with the TV remote are not
  tracked.
- **Volume state is assumed.** `volume_info` is not supported on the tested
  firmware. Mute can be tracked from IR.
- **Wake-on-LAN did not work on the tested model.** Other 2011 models may differ.
- Some firmware invalidates the pairing key after standby. If yours does this on
  every power cycle, use IR or RS-232C for daily power control.

## State and entities

The media player state is `on`, `off`, or `unknown`. The channel and input are
attributes:

| Attribute | Example |
|---|---|
| `source` | `HDMI1` |
| `media_channel` | `21` |
| `media_title` | `VEO 7`, `Channel 21`, or `HDMI1` |
| `ui_mode` | `VolCh` or `TouchPad` |
| `is_volume_muted` | `true` / `false` |

See [state and dashboard](docs/state-and-dashboard.md) for cards that show the
channel instead of only “Encendido”.

### `media_player`

- `turn_off`
- `volume_up` / `volume_down`
- `volume_mute`
- `play_media` with `media_content_type: channel`
- `select_source` for direct and configured sources

### `button` and `remote`

Buttons cover common navigation, digits, HDMI1–HDMI4, and Up/Down. The remote
entity accepts named keys such as `POWER`, `HDMI1`, `UP`, `OK`, and raw
two-digit decimal codes from `00` to `99`.

### IR service

```yaml
action: lg_netcast_hdcp.process_ir_key
target:
  entity_id: media_player.lg_tv
data:
  key: HDMI1
```

The action only updates state; it does not send a key to the TV.

## Security

This integration is local-only, but the HDCP protocol is unencrypted HTTP on
port 8080. Keep the TV on a trusted LAN, do not expose port 8080 to the internet,
protect Home Assistant backups, and never share a pairing key or session ID.

See [SECURITY.md](SECURITY.md).

## Documentation

| Guide | What it covers |
|---|---|
| [Configuration](docs/configuration.md) | Options, power-on, Apple TV/CEC, input sources |
| [IR receiver](docs/ir-receiver.md) | Wiring, ESPHome, code capture, debounce, testing |
| [State and dashboard](docs/state-and-dashboard.md) | Attributes, cards, templates |
| [Troubleshooting](docs/troubleshooting.md) | Symptom/cause/fix tables and logs |
| [FAQ](docs/faq.md) | Short answers |
| [Protocol](docs/protocol.md) | Endpoints, XML, state queries |
| [Key codes](docs/keycodes.md) | Tested key matrix |

See [docs/README.md](docs/README.md) for the full documentation index and
glossary.

## Troubleshooting quick table

| Symptom | Fix |
|---|---|
| No pairing key | TV must be on; check IP and port 8080 |
| `Unauthorized` | Retry; reauthenticate if the key was rejected |
| TV will not turn on | Configure IR, CEC, Wake-on-LAN, or RS-232C |
| Apple TV does not wake the TV | Set **Source before power off** to `HDMI1` |
| Only “Encendido” is visible | The channel is an attribute; use a state card |
| Channel empty on HDMI | Expected; use source or IR tracking |
| IR does not update state | Check wiring, logs, action, and key name |

More details: [troubleshooting](docs/troubleshooting.md). If you open an issue,
use the bug report template and never include a pairing key or session ID.

## Development

Development instructions, tests, protocol rules, and release steps are in
[CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

```bash
ruff check .
ruff format --check .
pytest
```

## License

MIT. See [LICENSE](LICENSE).

LG and NetCast are trademarks of LG Electronics. This project is unofficial and
is not endorsed by LG.
