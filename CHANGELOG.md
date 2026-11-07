# Changelog

## Unreleased

- Poll power, channel, channel name, and UI mode from the HDCP data endpoint.
- Added confirmed direct-input keys for HDMI1-HDMI4 and Up/Down keys.
- Added `lg_netcast_hdcp.process_ir_key` for optional external IR receiver
  state tracking.
- Added a source-before-power-off option so an HDMI-CEC source can wake the TV
  from standby.
- Added a repair issue explaining the remaining state limitations when IR
  tracking is not enabled.
- Mark the media player as on after a configured Wake-on-LAN or custom-action
  power-on.
- Report `unknown` instead of `off` when a command cannot reach the TV, and
  keep the state unchanged when a power-on action fails.
- Documented that Wake-on-LAN does not wake the tested 42LW650S-ZC; use IR,
  HDMI-CEC, or RS-232C.

## 0.3.0

- Corrected the key map to the verified decimal codes for the 42LW650S-ZC.
- Added documentation with the full tested key matrix and unknown codes.
- Limited raw key input to decimal codes `00`-`99`; letter suffixes are rejected.
- Added confirmed buttons for Q.Menu, Timer, TV/Radio, and Exit.
- Removed unverified playback features and buttons.

## 0.2.0

- Added remote-key buttons for navigation, input, channels, and digits.
- Added configurable input-source key sequences.
- Added optional Wake-on-LAN and custom-action power-on.
- Hide the turn-on feature when no power-on method is configured.
- Added a model profile structure for future television families.
- Added fixed-IP guidance to the setup and reconfiguration forms.
- Removed the external turn-on trigger in favor of configurable power-on
  methods.

## 0.1.0

- Initial release.
- HDCP pairing and session handling for LG NetCast 2.0 (2011) televisions.
- Media player entity with power, volume, mute, playback, and channel tuning.
- Remote entity with named and raw hexadecimal key codes.
- Device turn-on trigger for external IR, Wake-on-LAN, HDMI-CEC, or RS-232C
  actions.
- Reauthentication and reconfiguration flows.
- Redacted diagnostics.
- Standalone probe tool.
