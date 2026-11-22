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
Copy `custom_components/denonavr/` to `/config/custom_components/denonavr/` on Home Assistant and
restart. It overrides the built-in integration (same domain), so the existing "AV 20" entry keeps
working. It is a copy of HA **2026.11.2**: after an HA update, refresh it from the new core version
before restarting. The integration's "Use Telnet connection" option must be on for the Dirac select.

New entity: `select.av_20_dirac_live_filter`. Options are "Off" plus the filter names from Dirac Live
(falls back to "Slot n" until the receiver pushes the names, e.g. after an input change).

## Tests
```
pip install pytest                      # parser tests only (Python 3.11+)
pytest tests/test_dirac_slots.py
pip install -r requirements_test.txt    # + Home Assistant entity tests (Python 3.14)
pytest
```
