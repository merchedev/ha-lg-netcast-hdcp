# FAQ

## Does this integration support my LG TV?

It is for LG NetCast 2.0 televisions from 2011 that expose the HDCP HTTP server
on port `8080`. The tested model is the 42LW650S-ZC (firmware 0001.0009).

For 2012–2013 NetCast 3.0/4.0 televisions, use the official `lg_netcast`
integration.

## Can the integration turn the TV on?

Not over the HDCP protocol. The HTTP server stops in standby. Use IR, HDMI-CEC,
Wake-on-LAN (if supported), or RS-232C as a custom power-on action.

## Do I need an IR receiver?

No, not for power, channel, or UI mode. The integration polls those while the TV
is on.

An IR receiver is useful when you want to know:

- which HDMI input is active after a change made with the TV remote;
- mute changes made with the remote;
- key presses immediately rather than at the next poll.

Without IR, input changes made with the TV remote are not tracked. Changes made
from Home Assistant are tracked.

## Do I need `input_sources`?

It is optional for the confirmed direct inputs:

- `HDMI1`–`HDMI4` and `AV1` are in the source selector automatically.
- `select_source` and `Source before power off` work with those names without a
  mapping.
- The HDMI1–HDMI4 buttons and `remote.send_command: HDMI1` do not need it.

Use `input_sources` for a custom name, a non-direct input, or IR tracking of the
TV input menu.

For a custom source, map the name to the sequence the TV needs:

```yaml
input_sources:
  Satellite:
    - INPUT
    - RIGHT
    - OK
```

For IR tracking of a direct input menu, use the sequence the TV uses:

```yaml
input_sources:
  HDMI1:
    - INPUT
    - LEFT
    - OK
```

## Why do I only see “Encendido” / “On”?

The main media player state is power. The channel and source are attributes.
Check **Developer Tools → States → `media_player.lg_tv` → attributes**.

The media-control card shows `media_title` and `media_channel` when they are
available. `media_title` combines the channel and program names, for example
`VEO 7 · Noticias`. See [state-and-dashboard.md](state-and-dashboard.md).

## Why does the channel show as “Channel 3” instead of its name?

The TV did not include a channel name in the `cur_channel` response. The
integration also reads `chname`, `progName`, and similar fields, then tries the
TV channel list once. If none of them provide a name, it falls back to
`Channel <number>`.

After changing channels from Home Assistant, the integration refreshes the state
about three seconds later. The channel number updates immediately; the name and
program follow when the TV reports them.

If the name never appears, enable debug logging for
`custom_components.lg_netcast_hdcp.coordinator` and check the `Channel data:`
line. It contains the channel XML without the session ID.

## Why is the channel empty on HDMI?

The TV returns invalid channel data on external inputs. The same sentinel values
appear on HDMI1 and HDMI4, so the integration knows it is not on live TV but
cannot tell which HDMI port is active.

## Why does the integration not show the volume?

`volume_info` returns `400 Bad Request` on the tested firmware. Volume level is
not available. Mute can be tracked from an IR receiver.

## Does it work with an Apple TV?

Yes, as an HDMI-CEC power-on method. Configure the Apple TV `media_player.turn_on`
action as the custom power-on action and set **Source before power off** to the
Apple TV input, for example `HDMI1`.

The TV must be on that input when it enters standby for CEC to wake it again.
See [configuration.md](configuration.md#apple-tv-and-other-hdmi-cec-sources).

## Does it need the cloud?

No. All communication is local: HDCP HTTP on port `8080`, plus the local ESPHome
device if you use IR. There are no cloud dependencies.

## Is it secure?

The protocol is unencrypted HTTP on your local network. The pairing key and
session are sensitive. Keep the TV on a trusted network, do not expose port
`8080` to the internet, protect Home Assistant backups, and do not share the
pairing key or session. See [SECURITY.md](../SECURITY.md).

## Can I control more than one TV?

Yes. Add one config entry per TV. The IR action can target a specific media
player, device, or area.

## Why is there a repair issue about state tracking?

It appears when **IR receiver state tracking** is off. It explains that the
active HDMI input and volume are not available. Configure IR and use the issue's
**Fix** action, or dismiss the issue.

## How do I update?

Update through HACS and restart Home Assistant. The HACS/update dialog shows
the matching `CHANGELOG.md` section for the new version. New buttons and options
appear after the restart. See [configuration.md](configuration.md) for upgrade
notes.

## How do I reset the pairing?

A factory reset changes the pairing key. Start the reauthentication flow and
enter the new key shown by the TV. If the key is invalidated after standby, see
[troubleshooting.md](troubleshooting.md).
