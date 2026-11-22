# Plan

## Phase 0: Probe the AV 20 (read-only) ✅ done 2026-11-22
- [x] Disable the HA `denonavr` integration (or its telnet option) temporarily
- [x] Run `python tools/telnet_probe.py <AV20-IP> --listen 120`
- [x] While listening, on the remote: change input, change Dirac slot, change sound mode, toggle Dynamic EQ
      or other settings. Each change should appear as an event line
- [x] Commit the log to `captures/` and update `docs/protocol-notes.md` with verified formats
- [ ] Re-enable the integration (still disabled in HA as of 2026-11-22 22:50)

## Phase 1: Custom component (override core `denonavr`)
- [x] Find Markus's HA version (2026.11.2); copy `homeassistant/components/denonavr` at that tag into
      `custom_components/denonavr/`; add `"version"` to manifest.json (required for custom components)
- [x] Check which `denonavr` library version HA pins (1.3.3: it already has `dirac.dirac_filter`
      and `async_dirac_filter()`, so only slot names are missing upstream); read `foundation.py` and `const.py` at that version
- [x] Add Dirac filter support (went with a: no library patch; `dirac_slots.py` parses OPDLS lines
      from the library's "OP" telnet callback), either:
      a) subclass/monkeypatch in the custom component (fast), or
      b) vendor a patched library and set it in manifest `requirements` (cleaner, matches upstream PR)
- [ ] New entities (first set):
  | Entity | Platform | Source |
  |---|---|---|
  | Dirac Live filter (Slot 1/2/3/Off) | select | `PSDIRAC` |
  | ✅ Sound mode (raw) | sensor | `MS` (already an attribute; promote to sensor) |
  | ✅ Speaker preset | select | `SPPR` (library has it) |
  | ECO mode | select | `ECO` (library has it) |
  | ✅ Dimmer | select | `DIM` (library has it) |
  | HDMI output | select | `VS` (library has it) |
  | Room size, Audio restorer, Delay | sensor/select | `PS…` (library has it) |
  | ✅ Input signal / sample rate / channels | sensor | candidates in protocol-notes; verify |
- [x] Dirac select options use the real filter names from `OPDLSSL{n}NAME` (fallback "Slot n"); attributes: filter type (ART), imported or empty
- [x] Sensors from verified events: `SYSDA` (input format), `SYSMI` (decoded mode), `SSINFAISSIG`,
      `SSINFAISFSV` (sample rate), `SSSMG`, `PSDELAY`; binary sensors "Dirac Live active" and setup menu
- [ ] Re-query `PSDIRAC ?` after input change if the receiver doesn't push it
- [x] Tests with captured lines as fixtures (Dirac select + parser)
- [x] Install on HA (via HACS custom repository), restart, verify (Dirac select, 2026-11-22)

## Phase 2: Upstream
- [ ] PR to `ol-iver/denonavr`: Dirac slot names/types (`OPDLSSL*`) + tests. (`dirac_filter` and its
      setter already exist upstream since before 1.3.3)
- [ ] PR to `home-assistant/core`: select/sensor platforms for denonavr (follow the HA
      integration quality scale; one platform per PR is easier to review)
