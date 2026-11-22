# denonavr-dirac-ha

Extends the Home Assistant Denon/Marantz (`denonavr`) integration with the active Dirac Live filter slot
and other receiver settings. Target device: Marantz AV 20 at 10.1.1.22.

Start here: `CLAUDE.md` (context and rules), `docs/PLAN.md` (phases), `docs/protocol-notes.md`.

Quick start (Phase 0), in PowerShell from the repo root:
```powershell
# 1. In HA, disable the "AV 20" Denon AVR integration entry (receiver allows only one telnet connection)
.\tools\run_probe.ps1 -Note first-probe
#    (or: python tools/telnet_probe.py 10.1.1.22 --listen 120 --note first-probe)
# 2. While it listens: change input, Dirac slot and sound mode on the remote
# 3. Re-enable the integration in HA
```
If PowerShell blocks the .ps1 script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Install the custom component (Phase 1)

### With HACS (recommended)
1. HACS > the three-dot menu (top right) > **Custom repositories**.
2. Repository: `https://github.com/maukora/MarantzHA`, type **Integration** > **Add**.
3. Open "Denon AVR with Dirac Live (AV 20)" in HACS > **Download**, then restart Home Assistant.
4. HA shows a "custom integration overrides core denonavr" warning in the log. That's expected.

### Manually
Copy `custom_components/denonavr/` to `/config/custom_components/denonavr/` and restart.

### Notes
It overrides the built-in integration (same domain), so the existing "AV 20" entry keeps working. It is
a copy of HA **2026.11.2**: after an HA update, refresh it from the new core version before restarting
(or uninstall it in HACS to go back to the built-in one). The integration's "Use Telnet connection"
option must be on for the Dirac select.

### Entities added (all push-updated over telnet; need "Use Telnet connection")
| Entity | What it shows | From |
|---|---|---|
| `select.av_20_dirac_live_filter` | Active Dirac slot, labelled with the Dirac Live filter names | `PSDIRAC`, `OPDLSSL*` |
| `binary_sensor.av_20_dirac_live_active` | On when a filter is really applied (off in Direct/Pure Direct or Dirac Off) | `PSDIRAC` + `MS` |
| `sensor.av_20_input_audio_format` | Incoming format, e.g. "Dolby Atmos", "PCM" | `SYSDA` |
| `sensor.av_20_decoded_mode` | What the receiver decodes, e.g. "Multi Ch In" | `SYSMI` |
| `sensor.av_20_input_signal` | Signal type (attribute `code`) | `SSINFAISSIG` |
| `sensor.av_20_sample_rate` | Sample rate in kHz | `SSINFAISFSV` |
| `sensor.av_20_smart_select_group` | Movie / Music / Game | `SSSMG` |
| `sensor.av_20_sound_mode_raw` | Sound mode as the receiver names it | `MS` |
| `sensor.av_20_audio_delay` | Audio delay in ms (per input) | `PSDELAY` |
| `select.av_20_display_dimmer` | Front display brightness | `DIM` |
| `select.av_20_speaker_preset` | Speaker preset 1/2 (changes what you hear) | `SPPR` |
| `binary_sensor.av_20_setup_menu_open` | Setup menu open on screen | `MNMEN` |
| `sensor.av_20_<speaker>_level` / `_distance` | Per-speaker channel level (dB) and distance (m), one pair per configured speaker; Dirac stores these per filter | `SSLEV*`, `SSSDE*` |

The Dirac select falls back to "Slot n" until the receiver pushes the names (e.g. after an input
change). The receiver has no known query for `SYSDA`/`SYSMI`, so those show "unknown" after an HA
restart until the next signal change.

## Second probe: speaker setup
Crossovers, speaker sizes and subwoofer settings weren't in the first probe. To capture them,
disable the "AV 20" entry in HA, then run (read-only `?` queries only):
```powershell
.\tools\run_probe.ps1 -Note speakers -Set speakers -Listen 60
```
Re-enable the entry afterwards and commit the new file in `captures/`.

## Tests
```
pip install pytest                      # parser tests only (Python 3.11+)
pytest tests/test_dirac_slots.py
pip install -r requirements_test.txt    # + Home Assistant entity tests (Python 3.14)
pytest
```

## License
Apache License 2.0, the same as Home Assistant. `custom_components/denonavr/` is based on the Home
Assistant core `denonavr` integration (© Home Assistant contributors, Apache-2.0).
