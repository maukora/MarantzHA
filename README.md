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
