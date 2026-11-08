# Configuration

This guide covers the Home Assistant options for the LG NetCast HDCP
integration. For a first install, start with the [README](../README.md).

## Before you start

- The TV must be on and reachable on TCP port `8080`.
- Home Assistant and the TV should be on the same trusted local network.
- Use a static IP address or a DHCP reservation for the TV.
- You need the six-character pairing key shown by the TV during setup.

## Initial setup

1. In Home Assistant, open **Settings → Devices & services**.
2. Select **Add integration** and search for **LG NetCast HDCP**.
3. Enter the TV IP address.
4. The TV displays a six-character pairing key. Enter it in Home Assistant.
5. The integration creates a media player, a remote entity, and remote-key
   buttons.

If the TV rejects the stored key later, Home Assistant starts a
reauthentication flow. Turn the TV on, wait for it to finish booting, and enter
the new key shown on screen.

## Options reference

Open **Settings → Devices & services → LG NetCast HDCP → Configure**. The
dialog is split into **Power-on behavior**, **Input sources**, and **State
tracking**. Each section saves independently, so you can change only what you
need.

| Section | Option | Values | Default | Purpose |
|---|---|---|---|---|
| Power-on behavior | Power-on method | None, Wake-on-LAN, Custom action, Both | None | How `turn_on` wakes the TV |
| Power-on behavior | MAC address | MAC string | Empty | Wake-on-LAN target |
| Power-on behavior | Broadcast address | IPv4 address | `255.255.255.255` | Wake-on-LAN broadcast |
| Power-on behavior | Broadcast port | 1–65535 | `9` | Wake-on-LAN port |
| Power-on behavior | Custom turn-on action | Home Assistant action | Empty | IR, CEC, RS-232C, or script |
| Input sources | Input sources | Mapping of names to key sequences | Empty | Custom sources, non-direct inputs, and IR sequences |
| Input sources | Source before power off | Direct input or custom source | None | Leave the TV on a CEC input before standby |
| State tracking | IR receiver state tracking | Boolean | Off | Acknowledge external IR state updates and hide the warning |

## Power-on methods

### None

The turn-on feature is hidden. Turn-off still works over the HDCP protocol.

### Wake-on-LAN

Enter the TV Ethernet MAC address, broadcast address, and port. The integration
sends a magic packet when `turn_on` is requested.

Wake-on-LAN was tested on the 42LW650S-ZC (firmware 0001.0009) and the TV did
not wake. Other 2011 models may behave differently. If it does not work, use a
custom action.

### Custom action

Select an existing Home Assistant action. Common choices:

- an ESPHome IR transmitter;
- `media_player.turn_on` on an Apple TV or another HDMI-CEC source;
- a `remote.send_command` action for an IR blaster;
- an RS-232C script;
- an `hdmi_cec` action if Home Assistant has a CEC adapter.

The selected integration must already be configured and working.

### Both

Send Wake-on-LAN and then run the custom action.

After the action completes, the media player marks the TV as on. The state is
optimistic until the next state poll confirms it. The integration schedules one
refresh about 15 seconds after a configured power-on action, and then polls every
30 seconds. The HDCP server takes about 10–15 seconds to start after the TV
powers on; add a delay before sending keys.

## Apple TV and other HDMI-CEC sources

A CEC source can wake the TV only when the TV is left on that source. A typical
Apple TV setup on HDMI1:

1. On the TV, enable **SIMPLINK (HDMI-CEC)** and **Auto Power Sync** or the
   automatic power-on setting. Menu names vary by firmware.
2. On the Apple TV, enable **Settings → Remotes and Devices → Control TVs and
   Receivers**.
3. Add the Apple TV to Home Assistant.
4. In the LG integration options, set **Power-on method** to **Custom action**
   and select `media_player.turn_on` for the Apple TV entity.
5. Set **Source before power off** to `HDMI1`.

When Home Assistant turns off the TV, it first selects `HDMI1`, waits about two
seconds, and then sends `POWER`. The next time the Apple TV wakes, CEC can turn
the TV on again.

This only applies when Home Assistant performs the power-off. If you turn the
TV off with its own remote on another input, the integration cannot select the
CEC source first.

If the Apple TV stays on while the TV is off, waking it may not generate a new
CEC event. Turn the Apple TV off too, or use IR, RS-232C, or a USB-CEC adapter.

## Input sources

`HDMI1`–`HDMI4` and `AV1` are available automatically on the tested model. The
source selector includes them without any configuration, and the integration
sends their confirmed direct keys.

`input_sources` is now only needed for:

- an input without a confirmed direct key;
- a custom display name for a source;
- the TV input-menu sequence used by the IR receiver.

Example for a custom name:

```yaml
input_sources:
  Satellite:
    - INPUT
    - RIGHT
    - OK
```

If the custom name maps to a direct input, the direct key still works. For
example, `HDMI 1` maps to the `HDMI1` direct key.

To follow input changes made with the TV remote, configure the sequence used by
the TV input menu:

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

The integration still uses the direct key when selecting the source; the menu
sequence is used to recognise the change made with the remote. Names and
sequences are user-defined, and disconnected inputs may be disabled.

### Confirmed direct keys

| Source | Key |
|---|---|
| HDMI1 | `HDMI1` |
| HDMI2 | `HDMI2` |
| HDMI3 | `HDMI3` |
| HDMI4 | `HDMI4` |
| AV1 | `AV1` |

For more key names and raw codes, see [keycodes.md](keycodes.md).

## Source before power off

This option is intended for HDMI-CEC wake compatibility.

1. Select the source in **Source before power off**. `HDMI1`–`HDMI4` and `AV1`
   are offered directly.
2. If you use a custom source, add it in **Input sources** first.
3. Turn off the TV from Home Assistant.

The integration sends the source key or sequence, waits about two seconds, and
then sends `POWER`. The TV enters standby on that source.

The option only applies to power-off requests made by Home Assistant. The
integration cannot change the input after the TV has already entered standby.

## IR receiver state tracking

The HDCP data endpoint reports power, channel, channel name, and UI mode. It
does **not** report the active HDMI input or the volume. An external IR receiver
can fill the input and mute gaps. Direct inputs work without `input_sources`; add
the input-menu sequence only if you want to follow changes made with the TV
remote.

Configure the receiver to call:

```yaml
action: lg_netcast_hdcp.process_ir_key
target:
  entity_id: media_player.lg_tv
data:
  key: HDMI1
```

The action only updates state; it does not send IR. See
[ir-receiver.md](ir-receiver.md) for hardware, wiring, ESPHome configuration,
code capture, and troubleshooting.

After configuring the receiver, enable **IR receiver state tracking** to
suppress the state limitation repair issue. You can also use the **Fix** action
on that issue. The service works even when this option is off.

## Upgrading from 0.7.0

- `media_title` now combines the channel and program names when the TV reports
  them, for example `VEO 7 · Noticias`.
- `channel_name` and `program_name` are available as attributes.
- Changing channels from Home Assistant schedules a state refresh after about
  three seconds, so the name and program appear without waiting for the regular
  poll.
- If `cur_channel` has no name, the integration tries the TV channel list once.
- Restart Home Assistant after updating through HACS.

## Upgrading from 0.6.2

- The **Configure** dialog now opens a menu with **Power-on behavior**,
  **Input sources**, and **State tracking**. Each section saves independently.
- Spanish translations are included for setup, options, the IR service, the
  repair flow, and command errors.
- A failed command now reports an error and starts reauthentication when the TV
  rejects the session.
- Restart Home Assistant after updating through HACS.

## Upgrading from 0.5.0

- The state tracking repair issue now has a **Fix** action to enable IR
  receiver state tracking.
- The IR service key field offers common keys in a dropdown; type a raw code as
  a custom value.
- A state refresh runs about 15 seconds after a configured power-on action.
- Restart Home Assistant after updating through HACS.

## Upgrading from 0.4.1

- HDMI1–HDMI4 and AV1 appear in the source selector automatically.
- `input_sources` is optional for those direct inputs.
- **Source before power off** is now a selector; direct inputs do not need an
  input sources mapping.
- Keep `input_sources` for custom names, non-direct inputs, and IR sequences.
- Restart Home Assistant after updating through HACS.

## Upgrading from 0.4.0

- New HDMI1–HDMI4 buttons appear after the update.
- `media_title` now shows the source when the TV is on an external input and no
  channel is available.
- The state limitation repair issue appears when IR tracking is off. Dismiss it
  or configure IR tracking.
- Restart Home Assistant after updating through HACS.

## Related guides

- [IR receiver](ir-receiver.md)
- [State and dashboard](state-and-dashboard.md)
- [Troubleshooting](troubleshooting.md)
- [FAQ](faq.md)
