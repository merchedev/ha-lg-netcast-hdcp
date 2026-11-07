# State and dashboard

Home Assistant media players have one main state (`on`, `off`, `playing`, and so
on) plus attributes. The LG integration uses the main state for power and puts
the channel and input details in attributes.

## What the integration tracks

| Attribute | Example | Meaning |
|---|---|---|
| `state` | `on` / `off` / `unknown` | Power, polled or assumed |
| `source` | `HDMI1` | Known input source |
| `media_channel` | `21` | Current channel number |
| `media_title` | `VEO 7`, `Channel 21`, or `HDMI1` | Channel name, channel fallback, or input fallback |
| `ui_mode` | `VolCh` / `TouchPad` | TV UI mode |
| `is_volume_muted` | `true` / `false` | Mute, if known from IR |

The integration also exposes these services and controls:

- `media_player.select_source` for direct and configured sources;
- `media_player.play_media` with `media_content_type: channel`;
- `remote.send_command` for named keys and raw codes;
- `lg_netcast_hdcp.process_ir_key` for an external IR receiver;
- buttons for navigation, digits, HDMI1–HDMI4, and other confirmed keys.

## Why do I only see “Encendido” / “On”?

The main state is displayed by entity rows and some cards. It cannot be the
channel; Home Assistant expects a media player state such as `on` or `off`.
The channel and source are attributes.

If you are looking at a media-control card and see no channel, check:

1. Is the TV on a normal channel? On HDMI, `media_channel` is empty by design.
2. Has the 30-second state poll or the refresh after power-on run?
3. Does `media_player.lg_tv` show `media_channel` in
   **Developer Tools → States**?
4. Is `media_title` showing the source (`HDMI1`) instead of a channel?

## Where to see the attributes

1. Open **Developer Tools → States**.
2. Find `media_player.lg_tv`.
3. Expand `attributes`.

This is the authoritative view. The standard media-control card shows
`media_title` and, for a channel, `media_channel` as a secondary line. Entity
rows and entities cards show the main state only.

## Dashboard examples

### Media-control card

```yaml
type: media-control
entity: media_player.lg_tv
```

On live TV this shows the channel name (or “Channel 21”) and the channel number.
On HDMI1 it shows the input fallback if the source is known.

### Entities card with attributes

```yaml
type: entities
entities:
  - type: attribute
    entity: media_player.lg_tv
    attribute: media_channel
    name: Channel
  - type: attribute
    entity: media_player.lg_tv
    attribute: media_title
    name: Name
  - type: attribute
    entity: media_player.lg_tv
    attribute: source
    name: Source
  - type: attribute
    entity: media_player.lg_tv
    attribute: ui_mode
    name: UI mode
```

### Markdown card

```yaml
type: markdown
content: |
  **Channel:** {{ state_attr('media_player.lg_tv', 'media_channel') or '—' }}
  **Name:** {{ state_attr('media_player.lg_tv', 'media_title') or '—' }}
  **Source:** {{ state_attr('media_player.lg_tv', 'source') or 'TV' }}
  **UI:** {{ state_attr('media_player.lg_tv', 'ui_mode') or '—' }}
```

### Mushroom media player

```yaml
type: custom:mushroom-media-player-card
entity: media_player.lg_tv
use_media_info: true
```

Enable `use_media_info` so the card uses the media title instead of only the
entity state.

### Button-card with the channel as the main text

```yaml
type: custom:button-card
entity: media_player.lg_tv
name: |
  [[[
    const a = states['media_player.lg_tv'].attributes;
    return a.media_channel
      ? `Channel ${a.media_channel}`
      : (a.source || 'TV');
  ]]]
```

### Template sensors

```yaml
template:
  - sensor:
      - name: "LG TV Channel"
        state: "{{ state_attr('media_player.lg_tv', 'media_channel') }}"
      - name: "LG TV Source"
        state: "{{ state_attr('media_player.lg_tv', 'source') or 'TV' }}"
      - name: "LG TV UI"
        state: "{{ state_attr('media_player.lg_tv', 'ui_mode') }}"
```

These sensors can be shown in any card and are easier for screen readers than a
long entity state row.

## Automations

### Trigger when the channel changes

```yaml
trigger:
  - platform: state
    entity_id: media_player.lg_tv
    attribute: media_channel
```

### Trigger when the input changes

```yaml
trigger:
  - platform: state
    entity_id: media_player.lg_tv
    attribute: source
```

### Wait for the channel

```yaml
action:
  - wait_template: >-
      {{ state_attr('media_player.lg_tv', 'media_channel') == '21' }}
    timeout: "00:00:40"
```

## Limitations

- The active HDMI input is not reported by the data endpoint. On HDMI1 and
  HDMI4 the TV returns the same invalid channel data. The integration knows
  “external input” but not which one.
- Without an IR receiver, an input change made with the TV remote is not
  tracked. Selecting the source from Home Assistant, using a direct key, or
  using `Source before power off` keeps the source known.
- `volume_level` is not available. `volume_info` returns `400` on the tested
  firmware. `is_volume_muted` can be tracked from IR.
- The channel response is invalid in some UI states. The integration then
  shows no channel and keeps the last known source.
- Attributes disappear when the media player is off, as with other Home
  Assistant media players.

## Accessibility

- Use text labels in cards; do not rely on color alone.
- Prefer a Markdown card or template sensor if you need the channel read aloud
  by a screen reader.
- Keep source names short and meaningful.
- The entity names and button names are translated by Home Assistant; the
  integration only sets stable English entity names.
