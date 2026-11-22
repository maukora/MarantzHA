# denonavr-dirac-ha

Extends the Home Assistant Denon/Marantz (`denonavr`) integration with the active Dirac Live filter slot
and other receiver settings. Target device: Marantz AV 20.

Start here: `CLAUDE.md` (context and rules), `docs/PLAN.md` (phases), `docs/protocol-notes.md`.

Quick start (Phase 0):
```
# 1. Disable the denonavr integration in HA (the receiver allows only one telnet connection)
python tools/telnet_probe.py <AV20-IP> --listen 120 --note first-probe
# 2. While it listens: change input, Dirac slot and sound mode on the remote
# 3. Re-enable the integration
```
