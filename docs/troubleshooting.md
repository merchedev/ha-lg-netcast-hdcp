# Troubleshooting

Start with the quick checks:

- The TV is on and connected to the same network as Home Assistant.
- TCP port `8080` is reachable from Home Assistant.
- The integration version is 0.7.1 or newer.
- Home Assistant was restarted after updating through HACS.
- You are looking at the media player attributes in
  **Developer Tools → States**, not only at the entity row.

## Quick symptom table

| Symptom | Likely cause | Fix |
|---|---|---|
| No pairing key appears | TV off, wrong IP, port blocked | Turn TV on, check IP, test port 8080 |
| `Unauthorized` | Session expired or key rejected | Wait, retry; reauthenticate if needed |
| TV turns off but not on | HDCP server is off in standby | Configure IR, CEC, WoL, or RS-232C |
| Apple TV does not wake TV | TV was left on another input | Set **Source before power off** to the CEC input |
| Only “Encendido” is visible | Entity state, not attributes | Check attributes or use a state card |
| Channel is empty on HDMI | TV returns invalid channel data | Expected; use source/IR tracking |
| Source is empty after TV remote change | No IR tracking | Add IR receiver or select source in HA |
| Input selection does nothing | Sequence does not match menu | Use direct key or fix the sequence |
| IR codes appear but state does not change | Wrong service/key/entity | Check logs and test the action |
| Volume is unknown | `volume_info` is unsupported | Volume remains assumed; mute can use IR |
| Repair issue about state tracking | IR tracking is off | Configure IR or dismiss the issue |

## Pairing and authentication

### The TV does not show a pairing key

1. Make sure the TV is on and on the Home screen.
2. Check the IP address in the integration and in the router.
3. Check that Home Assistant can reach TCP port `8080`.
4. Run the probe tool from the repository:

   ```bash
   python3 tools/probe_hdcp.py --host TV_IP --pair
   ```

### `Unauthorized`

- The session expired. The integration should renew it automatically.
- If the pairing key was rejected, start the reauthentication flow.
- Wait 15–30 seconds after powering on before retrying. The HTTP server may not
  be ready yet.
- Some firmware invalidates the pairing key after standby. If this happens on
  every power cycle, use IR or RS-232C for daily power control.

### The pairing key is rejected after a factory reset

Factory reset changes the key. Start reauthentication and enter the new key
shown on screen.

## Power-on

### The TV turns off but does not turn on

The HDCP HTTP server stops in standby, so power-on cannot use the HDCP protocol.
Configure one of:

- **Custom action** with an IR blaster or ESPHome IR transmitter;
- **Custom action** with `media_player.turn_on` for an HDMI-CEC source;
- **Wake-on-LAN**, if your model supports it (the tested 42LW650S-ZC did not);
- **Custom action** with an RS-232C script.

### Apple TV or another CEC source does not wake the TV

1. Enable **SIMPLINK (HDMI-CEC)** on the TV.
2. Enable **Auto Power Sync** or the automatic power-on setting.
3. Enable **Control TVs and Receivers** on the Apple TV.
4. Set **Source before power off** to the Apple TV input, for example `HDMI1`.
5. Turn the TV off from Home Assistant, not from the TV remote on another input.

If the Apple TV stays on while the TV is off, waking it may not generate a new
CEC event. Turn the Apple TV off too or use IR/RS-232C.

### Wake-on-LAN does not work

The tested 42LW650S-ZC (firmware 0001.0009) did not wake with a magic packet.
Use a custom action instead. Check the MAC address and broadcast address if you
want to test another model.

## State

### The state stays off or unknown after turning on

- The integration marks the TV as on after the configured power-on action. The
  next state poll confirms it.
- The poll runs every 30 seconds. Home Assistant also schedules one refresh
  about 15 seconds after a configured power-on action.
- After an IR power-on, wait 10–15 seconds for the HDCP server to start before
  sending keys.
- If a command cannot reach the TV, the state becomes `unknown`. Check the IP
  and port.

### Only “Encendido” is visible

The main media player state is power, not the channel. See
[state-and-dashboard.md](state-and-dashboard.md) for cards that show
`media_channel`, `media_title`, and `source`.

On HDMI, `media_channel` is empty by design. The integration cannot tell which
HDMI port is active from the data endpoint. Use the source selector, direct
keys, or IR tracking.

### The channel name shows as “Channel 3”

The TV did not report a channel name in `cur_channel`. The integration reads
`name`, `chname`, `inputSourceName`, and `labelName`, then tries `channel_list`
once. If none of them contain the name, it falls back to `Channel <number>`.

To see what the TV sends, enable debug logging:

```yaml
logger:
  logs:
    custom_components.lg_netcast_hdcp.coordinator: debug
```

Change to the affected channel and look for the `Channel data:` line. It
contains the channel XML without the session ID. If the name is in a different
field, include that line when reporting the issue.

After changing channels from Home Assistant, the state refreshes after about
three seconds. The channel number updates immediately.

### The channel is empty on an HDMI input

Expected. The TV returns sentinel values on external inputs:

```xml
<data>
  <major>16368</major>
  <minor>65535</minor>
  <physicalNum>65535</physicalNum>
  <name></name>
</data>
```

The same values appear on HDMI1 and HDMI4, so they identify an external input
but not a specific port.

### The source remains old after using the TV remote

Without IR, the integration only knows input changes made by Home Assistant. Add
an IR receiver and configure the input menu sequence if you need exact tracking.

## Input selection

### Input selection does nothing

For `HDMI1`–`HDMI4` and `AV1`, the integration uses confirmed direct keys. These
inputs work without an `input_sources` mapping. If you use another source name,
the configured sequence must match your TV menu.

1. Test the keys with the `remote` entity.
2. Open the input menu and note the key presses that select the source.
3. Update the sequence in **Input sources**.
4. Save, reload the integration, and test again.

### Selecting the source works but the state does not change

The integration updates `source` after a successful key. If the TV does not
actually switch, check the sequence. The coordinator may also correct the state
on the next poll.

## IR receiver

See [ir-receiver.md](ir-receiver.md) for wiring, the ESPHome configuration, and
code capture.

### No codes in the ESPHome log

- Check the receiver is a 38 kHz module and is powered from 3.3 V.
- Check VCC, GND, and OUT; the pin order varies by module.
- Set `logger: level: DEBUG` and `dump: lg`.
- Try `dump: all` to see if another decoder recognises the remote.
- Check the remote batteries and distance.

### Codes appear but the media player does not change

- Confirm the ESPHome device is connected to Home Assistant.
- Confirm the action is `lg_netcast_hdcp.process_ir_key`.
- Confirm the `entity_id` and key name.
- Test the action from **Developer Tools → Actions**.
- Check the integration debug log.

### A key fires twice

Add a 300–500 ms debounce in ESPHome or in the Home Assistant automation.

### The repair issue does not disappear

The service works even when **IR receiver state tracking** is off. Enable the
option in the integration options after the receiver works. You can also
dismiss the issue if you do not need IR tracking.

## Volume

`volume_info` returns `400 Bad Request` on the tested firmware. The integration
does not use it. Volume level remains assumed. Mute can be tracked from IR.

## Repair issue

The issue appears when **IR receiver state tracking** is off. It explains that
the active HDMI input and volume are not available. You can:

- configure an IR receiver, then use the issue's **Fix** action to enable the
  option; or
- dismiss the issue if you do not need input/mute tracking.

## Logs and diagnostics

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.lg_netcast_hdcp: debug
```

Download diagnostics from **Settings → Devices & services → LG NetCast HDCP →
Download diagnostics**. The pairing key is redacted. Review the file before
sharing it.

**Never post the pairing key or session ID in an issue.** Do not enable verbose
`aiohttp` debug logging in public logs; the TV requires the session in a query
parameter.
