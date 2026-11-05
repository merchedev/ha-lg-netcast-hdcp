# Tested key codes

This document records the remote-key codes that were tested on a specific LG
NetCast 2.0 television. It exists so other users do not have to repeat the same
experiments.

## Tested model

- LG 42LW650S-ZC
- NetCast 2.0 (2011)
- Firmware 0001.0009
- LG HDCP HTTP server on TCP port 8080

## Important: decimal values, not hexadecimal

The television parses the `HandleKeyInput` value as a **decimal number** and
stops at the first non-digit character.

The valid range is:

```text
00 – 99
```

Consequences:

- `1A` is parsed as `1`, which is **channel down**.
- `9A` is parsed as `9`, which is **mute**.
- `A0` is parsed as `0`, which is **channel up**.
- `100` is rejected because it has three digits.

Do not send letters expecting separate functions. The reliable codes are
two-digit decimal strings.

## Confirmed codes

| Code | Function | Notes |
|---:|---|---|
| `00` | Channel up | |
| `01` | Channel down | |
| `02` | Volume up | |
| `03` | Volume down | |
| `04` | Unknown | No effect observed on live TV; not Up |
| `05` | Unknown | No effect observed on live TV; not Down |
| `06` | Right | |
| `07` | Left | |
| `08` | Power | |
| `09` | Mute | |
| `10` | Q.Menu | |
| `11` | Input | |
| `12` | Unknown | No effect observed |
| `13` | Unknown | No effect observed |
| `14` | Timer | Cycles off, 10, 20, 30, 60, 90, 120, 180, 240 minutes |
| `15` | TV/Radio | |
| `16` | Number 0 | |
| `17` | Number 1 | |
| `18` | Number 2 | |
| `19` | Number 3 | |
| `20` | Number 4 | |
| `21` | Number 5 | |
| `22` | Number 6 | |
| `23` | Number 7 | |
| `24` | Number 8 | |
| `25` | Number 9 | |
| `26` | TV/Radio | Duplicate of `15` |
| `27`–`29` | Unknown | |
| `30` | Favorite channel | |
| `31` | Unknown | |
| `32` | Teletext | |
| `33` | T.Opt | |
| `34` | Unknown | |
| `35` | OK | Duplicate of `68` |
| `36`–`37` | Unknown | |
| `38` | Time | Shows the time in the corner |
| `39` | Unknown | |
| `40` | Exit | Duplicate of `91` |
| `41`–`47` | Unknown | |
| `48` | AV mode | Cycles Cine/Game/etc. |
| `49`–`56` | Unknown | |
| `57` | Subtitle language | Cycles the subtitle language option |
| `58`–`66` | Unknown | |
| `67` | Home | |
| `68` | OK | Duplicate of `35` |
| `69` | Q.Menu toggle | Shows/hides Q.Menu |
| `70`–`76` | Unknown | |
| `77` | Picture mode | Cycles picture modes |
| `78`–`82` | Unknown | |
| `83` | List | Program list |
| `84` | Unknown | |
| `85` | Info | Channel, date, and time banner |
| `86`–`88` | Unknown | |
| `89` | Premium | |
| `90` | AV1 | |
| `91` | Exit | Duplicate of `40` |
| `92`–`96` | Unknown | Possibly colors or direct inputs; not confirmed |
| `97` | Blue | |
| `98` | Unknown | |
| `99` | Yellow | |

## Trailing letters are ignored

These were observed and are **not** separate functions:

| Code | Parsed as | Result |
|---|---:|---|
| `0A`–`0F` | `0` | Channel up |
| `1A`–`1F` | `1` | Channel down |
| `2A`–`2F` | `2` | Volume up |
| `3A` | `3` | Volume down |
| `6A` | `6` | Right |
| `7A` | `7` | Left |
| `8A` | `8` | Power |
| `9A` | `9` | Mute |
| `A0` | `0` | Channel up |

## Unknown or untested behaviour

The following functions were not found:

- Up and Down arrows
- Back
- Red and Green buttons
- Menu and Guide
- Play, Pause, and Stop
- Direct inputs other than AV1

The unknown codes above may require a menu to be open, may be unused on this
model, or may map to functions not tested. Do not assume they are safe to use
in automations.

## How to test a raw code

Use the `remote.send_command` action with one code at a time:

```yaml
action: remote.send_command
target:
  entity_id: remote.lg_tv_remote
data:
  command:
    - "24"
```

Put the TV on a live channel before testing number keys. Open a menu before
testing navigation keys. Note that codes above `99` are rejected.

## Integration mapping

The integration exposes only confirmed functions as buttons. The raw `remote`
entity accepts decimal codes from `00` to `99`; letter codes are rejected to
avoid the parser ambiguity described above.

This model profile is `hdcp_2011`. Future models should add a new profile or a
key override instead of changing the default map.

## Reporting new results

When reporting a new code, include:

- TV model
- NetCast/firmware version
- Code sent
- TV state (live TV, menu, app, input)
- Observed result
