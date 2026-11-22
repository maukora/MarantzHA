# Runs the read-only telnet probe against Markus's Marantz AV 20.
# BEFORE running: disable the "AV 20" Denon AVR integration entry in Home Assistant
# (Settings > Devices & services > Denon AVR Network Receivers > ... > Disable).
# The receiver only allows one telnet connection.
#
# Usage (from the repo root):  .\tools\run_probe.ps1            # 120 s, note "probe"
#                              .\tools\run_probe.ps1 -Note dirac-slots -Listen 180
param(
    [string]$Note = "probe",
    [int]$Listen = 120,
    [string]$AvrHost = "10.1.1.22"
)

$script = Join-Path $PSScriptRoot "telnet_probe.py"
Write-Host "Probing $AvrHost for $Listen s. Use the remote while it listens: change input, Dirac slot, sound mode." -ForegroundColor Cyan
python $script $AvrHost --listen $Listen --note $Note
Write-Host "Done. Remember to re-enable the integration in Home Assistant." -ForegroundColor Yellow
