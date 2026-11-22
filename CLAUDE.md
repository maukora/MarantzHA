# CLAUDE.md — denonavr-dirac-ha

## What this project is
This project extends the Home Assistant **Denon AVR Network Receivers** integration (domain `denonavr`,
built on the Python library `denonavr` from `ol-iver/denonavr`). The goal is for HA to show and control
more receiver state. The main item is **which Dirac Live filter slot is active** (Slot 1/2/3/Off), plus
other settings the library already reads but HA doesn't expose.

Target hardware: **Marantz AV 20** (AV preamp/processor with Dirac Live). The owner is Markus, based in
Finland. He has Dirac Live, REW and Home Assistant set up.

## Strategy (decided)
1. **Phase 0, probe:** capture the exact telnet lines the AV 20 sends for each setting. Use
   `tools/telnet_probe.py`. Save captures in `captures/`. Don't guess formats. Base the parsers on
   captured lines.
2. **Phase 1, custom component:** vendor the upstream HA `denonavr` integration into
   `custom_components/denonavr/`, using the **same domain** so it overrides core and existing config
   entries keep working. Add new entities there. Pin the vendored copy to the HA version Markus runs.
3. **Phase 2, upstream:** once it's stable, split the work into PRs. First `ol-iver/denonavr` (library:
   parse/set Dirac filter), then `home-assistant/core` (select/sensor entities). Follow each repo's
   contribution rules, tests and code style.

## Hard constraints
- **The receiver accepts only ONE telnet connection.** HA's `denonavr` integration keeps it open when
  "use telnet" is enabled. Before running the probe, disable the integration (or turn off telnet in its
  options), and re-enable it afterwards. Never write code that opens a second, parallel telnet session
  alongside the integration.
- Telnet port 23. Commands are ASCII, end with CR (`\r`), and receive responses/events of the same form.
  Leave ~50–100 ms between commands. Wait ~1 s after `PWON` before sending the next command.
- New entities must use push updates through the library's telnet callbacks, not polling, wherever the
  receiver sends events.
- Never send commands that change speaker setup, run calibration or reset the unit (`SYS RESET`, etc.).
  Don't test things like `SPPR` (speaker preset) or `PSDIRAC` switching until Markus confirms, because
  they change what he hears.
- Use entity names in English. HA translations go in `strings.json` / `translations/en.json`.
  Markus speaks Finnish, so add `fi.json` if it's cheap.

## Known protocol facts (verify against captures)
- Dirac filter: `PSDIRAC 1`, `PSDIRAC 2`, `PSDIRAC 3`, `PSDIRAC OFF`. Query: `PSDIRAC ?`.
  The Dirac filter is stored **per input source**, so the value changes when the input changes.
  Re-query or listen for the event after `SI` changes.
- The filter *names* set in the Dirac Live software are shown on the receiver's on-screen GUI. They are
  probably NOT exposed over telnet/HTTP. Plan for user-configurable slot labels in the options flow.
- In Direct/Pure Direct only distances and levels apply (no acoustic filter). Consider a derived
  "Dirac effective" attribute.
- See `docs/protocol-notes.md` for the full list of candidate commands.

## Repo layout
- `docs/PLAN.md`: phased plan and entity list. Keep it updated as tasks are done.
- `docs/protocol-notes.md`: commands and verified response formats.
- `tools/telnet_probe.py`: standalone probe (stdlib only, Python 3.11+).
- `captures/`: raw probe logs (`YYYYMMDD-HHMM-<note>.log`).
- `custom_components/denonavr/`: created in Phase 1.

## Working style
- Keep changes small and reviewable. Write unit tests for each new parser, using the captured lines as
  fixtures.
- Before changing upstream code, read how existing telnet settings are implemented in
  `denonavr/foundation.py` (e.g. `room_size`, `speaker_preset`, `eco_mode`) and copy that pattern.
- Ask Markus before anything that touches the live receiver beyond read-only `?` queries.
