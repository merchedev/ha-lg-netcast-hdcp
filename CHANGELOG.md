# Changelog

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
