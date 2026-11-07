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
- Tune to a channel by number.
- Poll power, the current channel, the channel name, and the TV UI mode from the
  HDCP data endpoint.
- Buttons for Home, OK, Input, Left/Right/Up/Down, channels, Q.Menu, Timer,
  TV/Radio, Exit, and digits.
- Direct input selection for HDMI1–HDMI4 and AV1.
- Configurable input-source key sequences for other inputs and IR tracking.
- Optional Wake-on-LAN or custom-action power-on.
- Optional external IR receiver state tracking.
- Optional source-before-power-off for HDMI-CEC wake compatibility.
- Send any supported remote key through a `remote` entity.
- Automatic session reauthentication after the TV wakes up.
- Reauthentication and reconfiguration flows.
- Redacted diagnostics.
- A standalone probe tool for troubleshooting.

## Limitations

- **Power on is not possible over this protocol.** The HTTP server stops when
  the TV enters standby. Configure Wake-on-LAN or a custom action (IR, CEC, or
  RS-232C). If no method is configured, the turn-on feature is hidden.
- **Wake-on-LAN does not work on every 2011 model.** It was tested on the
  42LW650S-ZC (firmware 0001.0009) and the TV did not wake. Use a custom
  action (IR, HDMI-CEC, or RS-232C) instead.
- Power, channel, and UI mode are queried while the TV is on. **The active HDMI
  input and the volume are not reported.** On an external input, the channel
  response is invalid, so the integration can tell “live TV” from “external
  input” but not which HDMI port is selected. Without an IR receiver, input
  changes made with the TV remote are not tracked.
- Volume state is assumed. The `volume_info` query is not supported by the
  tested firmware and returns `400 Bad Request`.
- Direct input keys are confirmed for HDMI1–HDMI4 and AV1 on the tested model.
  Other inputs still use user-configured key sequences.
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
method, define input sources, select a source before power off, and enable IR
receiver state tracking.

## Power on

Power-on is configured in **Settings → Devices & services → LG NetCast HDCP →
Configure**. Choose one of:

- **None**: the turn-on feature is hidden. Turn-off still works over NetCast.
- **Wake-on-LAN**: enter the TV's Ethernet MAC address, broadcast address, and
  port. The integration sends a magic packet when `turn_on` is requested.
  Wake-on-LAN does **not** work on the tested 42LW650S-ZC (firmware
  0001.0009): the TV stays in standby. Other 2011 models may behave
  differently.
- **Custom action**: select an existing Home Assistant action. This can be an
  ESPHome IR service, a `remote.send_command`, an HDMI-CEC action, an RS-232C
  script, or any other action. **The selected integration must already be
  configured and working before selecting this option.** This is the
  recommended method for the tested model.
- **Both**: send Wake-on-LAN and then run the custom action.

If no method is configured, no turn-on button is shown. Turn-off always uses
the NetCast HDCP protocol.

After the configured power-on method runs successfully, the media player marks
the TV as on. The state is optimistic until the next state poll confirms it. If
a later command cannot reach the TV, the state becomes `unknown` instead of
`off`.

The HDCP server takes several seconds to start after the TV powers on. The
integration polls power and channel every 30 seconds. If an automation sends
keys immediately after `turn_on`, add a delay of about 10–15 seconds before the
first command; otherwise the command fails and the state becomes `unknown`.
The integration renews the session automatically once the server is reachable
again.

### Apple TV and other HDMI-CEC sources

An HDMI-CEC source device can power on the TV if the TV is left on that source
when it enters standby. A typical setup with an Apple TV on HDMI1:

1. Enable `SIMPLINK (HDMI-CEC)` and `Auto Power Sync` / automatic power-on on
   the TV; the exact menu name varies by firmware.
2. Enable **Control TVs and Receivers** on the Apple TV.
3. In the integration options, set **Power-on method** to **Custom action** and
   select `media_player.turn_on` for the Apple TV entity.
4. Set **Source before power off** to `HDMI1`.

When Home Assistant turns off the TV, it first selects `HDMI1` and then sends
`POWER`. The next time the Apple TV wakes, CEC can turn the TV on again. This
only applies when Home Assistant performs the power-off; if you turn the TV off
with its own remote on another input, the integration cannot select the CEC
source first.

If the Apple TV remains on while the TV is off, waking it may not generate a new
CEC event. In that case, turn the Apple TV off too or use IR, RS-232C, or a
USB-CEC adapter.

### Input sources

The tested model has confirmed direct keys for HDMI1–HDMI4 and AV1. Configure
the source names you use in the same **Configure** dialog. If the name matches
`HDMI1`, `HDMI2`, `HDMI3`, `HDMI4`, or `AV1`, the integration sends the direct
key when you select that source:

```yaml
input_sources:
  HDMI1:
    - HDMI1
  HDMI2:
    - HDMI2
```

The sequence is still useful as a fallback and for IR state tracking. If you
want the integration to follow input changes made with the TV remote, configure
the sequence that the TV's input menu uses:

```yaml
input_sources:
  HDMI1:
    - INPUT
    - LEFT
    - OK
  HDMI2:
    - INPUT
    - LEFT
    - LEFT
    - OK
```

The integration uses the direct key for `HDMI1`–`HDMI4`/`AV1` when selecting a
source, and uses the configured sequence for other names or as a fallback.
Names and sequences are user-defined; disconnected inputs may be disabled and
menu order can vary.

### HDMI-CEC and RS-232C

- HDMI-CEC: use the `hdmi_cec` integration if Home Assistant is connected to the
  TV through a CEC-capable adapter. Select that action as the custom turn-on
  action. A source device such as an Apple TV can also wake the TV through its
  own CEC support; see the Apple TV section above.
- RS-232C: the 42LW650S has an RS-232C port. LG's serial protocol supports power
  on (`ka 01 01`), power off (`ka 01 00`), volume, and input selection. Expose
  it through a script or another integration and select that action.

## State tracking

While the TV is on, the integration queries:

```text
GET /hdcp/api/data?target=cur_channel&session=SESSION
GET /hdcp/api/data?target=context_ui&session=SESSION
```

This provides power, the current channel, the channel name, and the UI mode
(`VolCh` for normal TV, `TouchPad` for menus). On an external input the channel
response contains sentinel values (`major=16368`, `physicalNum=65535`, empty
name), so the integration knows it is not on live TV but cannot tell which HDMI
input is active.

If you change inputs with the TV remote, configure an external IR receiver to
forward the observed keys. The integration exposes this action:

```yaml
action: lg_netcast_hdcp.process_ir_key
target:
  entity_id: media_player.lg_tv
data:
  key: INPUT
```

The action **does not send a key to the TV**. It only updates the integration's
state. Use `remote.send_command` when you want to send a key.

The key can be a name such as `POWER`, `INPUT`, `LEFT`, `OK`, `NUMBER_1`,
`HDMI1`, or `UP`, or a two-digit decimal code. The integration matches the
observed keys against the configured `input_sources` sequences to update the
source. For example, if `HDMI1` is configured as `INPUT, LEFT, OK`, pressing that
sequence on the TV remote updates the source to `HDMI1`.

### ESPHome IR receiver

An ESPHome IR receiver can call the action directly. Map the codes captured from
your remote to the key names used by the integration:

```yaml
remote_receiver:
  pin: GPIOXX
  dump: lg
  on_lg:
    - if:
        condition:
          lambda: "return x.data == 0x20DF10EF;"
        then:
          - homeassistant.action:
              action: lg_netcast_hdcp.process_ir_key
              data:
                entity_id: media_player.lg_tv
                key: POWER
```

The code above is an example; capture the codes from your own remote. Repeat the
condition for each key. If your receiver reports a key more than once, debounce
it in ESPHome or in a Home Assistant automation.

After configuring the receiver, enable **IR receiver state tracking** in the
integration options. This suppresses the state limitation warning.

### State limitation warning

The HDCP protocol does not report the active HDMI input or the volume. When IR
state tracking is off, the integration creates a dismissible repair issue that
explains:

- Power, channel, and UI mode are available.
- The active HDMI input and volume are not.
- If the TV is turned on through HDMI-CEC (for example an Apple TV), then
  switched to another input and turned off with the TV remote, the CEC device
  may not be able to wake it again.
- **Source before power off** can keep the TV on the CEC input.
- An IR receiver and **IR receiver state tracking** improve input and mute
  tracking.

## Entities

### `media_player`

- `turn_off`
- `volume_up` / `volume_down`
- `volume_mute`
- `play_media` with `media_content_type: channel`
- `select_source` for configured input sources
- State attributes: `source`, `media_channel`, `media_title`, and `ui_mode`

The channel, channel name, and `ui_mode` are queried from the TV while it is on.
They disappear when the TV is off, as with other Home Assistant media players.

### `button`

Buttons are created for:

`Home`, `OK`, `Input`, `Left`, `Right`, `Up`, `Down`, `Channel up`,
`Channel down`, `Q.Menu`, `Timer`, `TV/Radio`, `Exit`, and digits `0`–`9`.

### `remote`

The remote entity accepts confirmed key names and raw decimal codes:

```yaml
action: remote.send_command
target:
  entity_id: remote.lg_tv_remote
data:
  command:
    - HOME
    - LEFT
    - OK
```

Supported names include:

`POWER`, `VOLUME_UP`, `VOLUME_DOWN`, `MUTE`, `CHANNEL_UP`, `CHANNEL_DOWN`,
`LEFT`, `RIGHT`, `UP`, `DOWN`, `OK`, `EXIT`, `HOME`, `INPUT`, `Q_MENU`,
`TIMER`, `TV_RADIO`, `LIST`, `INFO`, `PICTURE_MODE`, `AV_MODE`, `AV1`,
`HDMI1`, `HDMI2`, `HDMI3`, `HDMI4`, `BLUE`, `YELLOW`, and `NUMBER_0`
through `NUMBER_9`.

Raw codes are two **decimal** digits from `00` to `99`, for example `02` for
volume up. Letter suffixes are rejected: the TV parser would silently interpret
`1A` as `1`. The confirmed direct-input and Up/Down codes above `99` are
available through their names (`HDMI1`, `HDMI2`, etc.), not as raw codes.

See [docs/keycodes.md](docs/keycodes.md) for the full tested matrix.

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
feature is intentionally hidden. On the 42LW650S-ZC, Wake-on-LAN does not work;
use IR, HDMI-CEC, or RS-232C.

If you use an Apple TV or another HDMI-CEC source, set **Source before power
off** to the CEC input. Otherwise the TV may enter standby on another input and
the CEC device may not be able to wake it again.

### The state stays off or unknown after turning on

- The integration marks the TV as on after the configured power-on action
  completes. The next state poll confirms it.
- If the state becomes `unknown`, a command could not reach the TV. After an IR
  power-on, wait 10–15 seconds for the HDCP server to start before sending keys.
- Check that the TV is on and reachable on TCP port 8080.
- The state poll runs every 30 seconds. A TV that was turned on outside Home
  Assistant can take up to one poll interval to appear as on.

### The channel is empty on an HDMI input

Expected. The TV returns invalid channel data (`major=16368`,
`physicalNum=65535`, empty name) on external inputs. The integration can tell
that it is not on live TV, but the protocol does not report which HDMI input is
active. Use the source selector, direct input keys, or an IR receiver to track
the input.

### Input selection does nothing

For `HDMI1`–`HDMI4` and `AV1`, the integration uses confirmed direct keys. If
you use another source name, the input menu has to be open and the key sequence
must match your TV's current input layout. Disconnected inputs are often
disabled, so the number of navigation presses changes. Adjust `input_sources`
with the `remote` entity or the confirmed navigation buttons, then update the
sequence.

### The state tracking repair issue appears

The issue is created when **IR receiver state tracking** is off. It explains
that the active HDMI input and volume are not available through the HDCP
protocol. Configure an IR receiver to call `lg_netcast_hdcp.process_ir_key` and
enable the option, or dismiss the issue if you do not need input tracking.

### Volume commands return `200 OK` but nothing happens

The command endpoint returns `200` for accepted requests even when a key is not
handled. Use the **decimal** codes confirmed for this model. Raw codes above
`99` and letter suffixes are rejected; use the named direct-input and Up/Down
keys instead. The `volume_info` query is not supported on the tested firmware,
so the volume state remains assumed.

## Debug logging

```yaml
logger:
  logs:
    custom_components.lg_netcast_hdcp: debug
```

Pairing keys and session IDs are never logged.

## Protocol documentation

See [docs/protocol.md](docs/protocol.md) for endpoints, XML payloads, and session
behavior. See [docs/keycodes.md](docs/keycodes.md) for the tested key matrix.

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
