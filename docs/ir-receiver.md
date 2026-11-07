# Connecting an IR receiver

An external IR receiver is optional. The integration already reads power,
channel, channel name, and UI mode from the TV. An IR receiver is useful when
you want to follow:

- which HDMI input is active when you change it with the TV remote;
- mute changes made with the TV remote;
- remote key presses immediately, without waiting for the next poll.

It is **not** required for power, channel, or the Apple TV/CEC setup.

## How it works

```text
TV remote -> IR receiver -> ESPHome -> Home Assistant service
                                      -> media player state
```

The TV already receives the IR command directly. The ESP only tells Home
Assistant which key was pressed. The integration does **not** send IR back to
the TV.

## What you need

- An ESP32 or ESP8266 board supported by ESPHome.
- A 38 kHz IR receiver module, for example TSOP38238, VS1838B, or HX1838.
- Three jumper wires.
- Optional: a 100 Ω resistor in series with VCC and a 100 nF capacitor between
  VCC and GND for a more stable supply.
- The TV remote.
- The LG NetCast HDCP integration already set up in Home Assistant.

## Wiring

Check the pinout printed on your receiver module before connecting it. The
order varies between modules.

| Receiver pin | ESP32 / ESP8266 |
|---|---|
| VCC | `3V3` |
| GND | `GND` |
| OUT | `GPIO14` (or another input GPIO) |

```text
TSOP38238 / VS1838B        ESP32
VCC  (3.3 V)  -------------  3V3
GND           -------------  GND
OUT           -------------  GPIO14
```

Do not power a 3.3 V receiver from 5 V. If your module is a 5 V module, use a
level shifter or a 3.3 V-compatible receiver. The receiver output is typically
active low, which is why the ESPHome example uses `inverted: true`.

## ESPHome configuration

The following is a complete minimal example. Replace the Wi-Fi secrets, board,
and GPIO if needed.

```yaml
esphome:
  name: ir-receiver

esp32:
  board: esp32dev
  framework:
    type: esp-idf

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
  batch_delay: 0ms

logger:
  level: INFO

ota:
  - platform: esphome

remote_receiver:
  pin:
    number: GPIO14
    inverted: true
    mode:
      input: true
      pullup: true
  dump: lg
  tolerance: 50%
  filter: 250us
  idle: 4ms
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

Notes:

- `entity_id` must match your LG media player entity.
- `0x20DF10EF` is only an example. Capture the codes from your own remote.
- `homeassistant.action` is the current ESPHome action name. Older ESPHome
  versions may use `homeassistant.service`; use the name supported by your
  version.
- `api: batch_delay: 0ms` makes API events arrive without batching delay. It is
  optional.
- For an ESP8266, use the matching `esp8266:` board section and a safe GPIO.
- Create a `secrets.yaml` next to the ESPHome configuration with `wifi_ssid`
  and `wifi_password`, or replace the `!secret` lines with literal values in
  your private configuration.

## Capture the remote codes

1. Set `logger: level: DEBUG` temporarily.
2. Flash the ESPHome device and open its logs.
3. Point the TV remote at the receiver and press one key.
4. Look for a line like:

   ```text
   [D][remote.lg]: Received LG: data=0x20DF10EF, nbits=32
   ```

5. Write down the `data` value for each key.
6. Add one `if` condition per key, mapping the value to a key name.

Use only the keys you need. The integration accepts names such as `POWER`,
`INPUT`, `LEFT`, `RIGHT`, `UP`, `DOWN`, `OK`, `HOME`, `EXIT`, `MUTE`,
`CHANNEL_UP`, `CHANNEL_DOWN`, `NUMBER_0` to `NUMBER_9`, `HDMI1` to `HDMI4`,
and `AV1`. The service UI offers these common keys in a dropdown; type a
two-digit decimal code as a custom value when needed.

Example with two keys:

```yaml
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
    - if:
        condition:
          lambda: "return x.data == 0x20DF906F;"
        then:
          - homeassistant.action:
              action: lg_netcast_hdcp.process_ir_key
              data:
                entity_id: media_player.lg_tv
                key: INPUT
```

The second value is only an example; use the value captured from your remote.

## Test the service

You can test the Home Assistant side without the ESP:

1. Open **Developer Tools → Actions**.
2. Select `lg_netcast_hdcp.process_ir_key`.
3. Target your media player entity.
4. Enter a key such as `POWER` or `HDMI1`.
5. Run the action.

The media player state should update. The action does not send a key to the TV;
the TV must already be in the desired state.

## Debounce repeated keys

Some receivers report the same key more than once. If `POWER` toggles twice, or
`HDMI1` is processed repeatedly, add a debounce:

- in ESPHome, ignore repeated codes within 300–500 ms; or
- route the ESP event through a Home Assistant automation with `mode: single`
  and a short delay between calls.

Start with a 400 ms debounce and adjust it to your remote.

## Using ESPHome events instead of direct actions

If you prefer to keep the code mapping in Home Assistant, send an event from
ESPHome and use an automation to call the service:

```yaml
remote_receiver:
  pin:
    number: GPIO14
    inverted: true
  dump: lg
  on_lg:
    - homeassistant.event:
        event: esphome.ir_key
        data:
          code: !lambda "return format_hex(x.data);"
```

Then create an automation with a mapping from `code` to key name. This makes
the ESPHome YAML smaller and the mapping easier to edit in Home Assistant.

## Troubleshooting

### No IR codes in the ESPHome log

- Check VCC, GND, and OUT. The receiver needs 3.3 V.
- Confirm the receiver is 38 kHz and the output is connected to the GPIO in the
  YAML.
- Set `logger: level: DEBUG` and `dump: lg`.
- Try `dump: all` to see whether another protocol decoder recognises the remote.
- Check the remote batteries, distance, and angle.
- Some receiver modules have a different pin order; read the label.
- If the module is active high instead of active low, try `inverted: false`.

### Codes appear but the entity does not change

- Check that the ESPHome device is connected to Home Assistant.
- Check the action name and `entity_id`.
- Check the key name against the supported list.
- Check the integration logs with debug logging enabled.
- Test `lg_netcast_hdcp.process_ir_key` from Developer Tools.

### The key fires twice

- Add a 300–500 ms debounce in ESPHome or Home Assistant.
- Confirm the remote is not sending a repeat frame that you are mapping twice.

### The repair issue remains

The `IR receiver state tracking` option only suppresses the state limitation
warning. The service itself is always available. Enable the option after the
receiver works if you want the warning to disappear, or use the issue's **Fix**
action.

## Security

The IR path does not use the TV pairing key or session. The service only
updates Home Assistant state and does not send commands to the TV. IR is
one-way; the receiver cannot confirm that the TV changed state.
