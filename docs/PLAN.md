# Plan

## Phase 0: Probe the AV 20 (read-only)
- [ ] Disable the HA `denonavr` integration (or its telnet option) temporarily
- [ ] Run `python tools/telnet_probe.py <AV20-IP> --listen 120`
- [ ] While listening, on the remote: change input, change Dirac slot, change sound mode, toggle Dynamic EQ
      or other settings. Each change should appear as an event line
- [ ] Commit the log to `captures/` and update `docs/protocol-notes.md` with verified formats
- [ ] Re-enable the integration

## Phase 1: Custom component (override core `denonavr`)
- [ ] Find Markus's HA version; copy `homeassistant/components/denonavr` at that tag into
      `custom_components/denonavr/`; add `"version"` to manifest.json (required for custom components)
- [ ] Check which `denonavr` library version HA pins; read `foundation.py` and `const.py` at that version
- [ ] Add Dirac filter support, either:
      a) subclass/monkeypatch in the custom component (fast), or
      b) vendor a patched library and set it in manifest `requirements` (cleaner, matches upstream PR)
- [ ] New entities (first set):
  | Entity | Platform | Source |
  |---|---|---|
  | Dirac Live filter (Slot 1/2/3/Off) | select | `PSDIRAC` |
  | Sound mode (raw) | sensor | `MS` (already an attribute; promote to sensor) |
  | Speaker preset | select | `SPPR` (library has it) |
  | ECO mode | select | `ECO` (library has it) |
  | Dimmer | select | `DIM` (library has it) |
  | HDMI output | select | `VS` (library has it) |
  | Room size, Audio restorer, Delay | sensor/select | `PS…` (library has it) |
  | Input signal / sample rate / channels | sensor | candidates in protocol-notes; verify |
- [ ] Options flow: labels for Dirac slots ("Slot 1" → e.g. "Movies – flat bass")
- [ ] Re-query `PSDIRAC ?` after input change if the receiver doesn't push it
- [ ] Tests with captured lines as fixtures
- [ ] Install on HA (copy to /config/custom_components), restart, verify

## Phase 2: Upstream
- [ ] PR to `ol-iver/denonavr`: `dirac_filter` property + `async_dirac_filter(slot)` setter + tests
- [ ] PR to `home-assistant/core`: select/sensor platforms for denonavr (follow the HA
      integration quality scale; one platform per PR is easier to review)
