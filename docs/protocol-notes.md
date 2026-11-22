# Protocol notes: Marantz AV 20 (Denon/Marantz telnet protocol)

Status legend: ✅ verified on AV 20 · ❓ candidate (from other models/integrations, unverified)

| Purpose | Query | Set examples | Status |
|---|---|---|---|
| Power | `PW?` / `ZM?` | `PWON`, `PWSTANDBY` | ❓ |
| Input | `SI?` | `SIGAME` | ❓ |
| Sound mode | `MS?` | `MSDOLBY DIGITAL` | ❓ |
| Master volume | `MV?` | `MV50` | ❓ |
| Channel levels | `CV?` | `CVFL 50` | ❓ |
| **Dirac Live filter** | `PSDIRAC ?` | `PSDIRAC 1/2/3/OFF` | ❓ (used by Unfolded Circle integration) |
| Dynamic EQ | `PSDYNEQ ?` | `PSDYNEQ ON` | ❓ (may not apply with Dirac) |
| Ref level offset | `PSREFLEV ?` | | ❓ |
| Dynamic volume | `PSDYNVOL ?` | | ❓ |
| LFE level | `PSLFE ?` | | ❓ |
| Bass / Treble / Tone | `PSBAS ?` `PSTRE ?` `PSTONE CTRL ?` | | ❓ |
| Dynamic range comp. | `PSDRC ?` | | ❓ |
| Audio delay | `PSDELAY ?` | | ❓ (library has it) |
| Room size | `PSRSZ ?` | | ❓ (library has it) |
| Audio restorer | `PSRSTR ?` | | ❓ (library has it) |
| Speaker preset | `SPPR ?` | `SPPR 1/2` | ❓ (library has it) |
| ECO | `ECO?` | `ECOON/AUTO/OFF` | ❓ |
| Dimmer | `DIM ?` | | ❓ |
| HDMI monitor out | `VSMONI ?` | | ❓ |
| Input signal info | `SSINFAISFSV ?`, `SSINFAISSIG ?` | | ❓ (seen on newer models) |
| Smart Select | `MSSMART ?` | | ❓ |

## Notes
- Dirac filter is stored per input source (Marantz/Denon manual).
- Dirac Live filter names appear in the receiver GUI; no known telnet/HTTP query for them.
- HTTP alternative for sending commands: `http://<ip>:8080/goform/formiPhoneAppDirect.xml?<CMD>`
  (send only, no readback). The AV 20 may also have an HTTPS API on port 10443; check whether it exposes
  more state (e.g. `/ajax/...` endpoints used by the web UI).

## Verified captures
(fill in from `captures/`)
