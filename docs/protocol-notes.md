# Protocol notes: Marantz AV 20 (Denon/Marantz telnet protocol)

Verified on Markus's AV 20 at 10.1.1.22 from `captures/20261122-2227-first-probe.log` and
`captures/20261122-2230-snd-probe.log`. ✅ = seen on AV 20 · ❌ = no reply · ❓ = unverified

## Dirac Live ✅ (main goal)
| Line | Meaning |
|---|---|
| `PSDIRAC ?` → `PSDIRAC 1` | Active slot: `1` / `2` / `3` / `OFF`. Also **pushed as an event** whenever the slot changes. |
| `OPDLSSL1NAME ALeft-HigherLowerShelfs` | **Filter name of slot 1**, right-padded with spaces (strip it). Empty name = empty slot. |
| `OPDLSSL1IMP ON` | Slot has a filter imported (`ON`/`OFF`). |
| `OPDLSSL1TYP ART` | Filter type: `ART` (Dirac Live Active Room Treatment); `NSA` seen on the empty slot (probably "not set"). Other values may exist (e.g. room correction only, bass control). |
| `OPDLS END` | End of the slot block. |

- The OPDLS block (slots 1–3) is **pushed unprompted** after input, sound mode and signal changes, and
  after leaving the setup menu. A direct query command is unknown. Try `OPDLS ?` (read-only).
- Markus's slots: 1 = "ALeft-HigherLowerShelfs" (ART), 2 = "ArendalLeft" (ART), 3 = empty.
- A slot change is followed by a full dump of `SSLEV*` (channel levels), `SSTTL*` (test tone levels) and
  `SSSDE*` (speaker distances, e.g. `SSSDEFL 0121`). Dirac stores levels and distances per filter. With
  `PSDIRAC OFF` the values were the generic ones (`SSSDEFL 0260`, `SSSDESTP 01M` vs `01S`).
- The slot is stored per input. `SI…` changes come with a new `PSDIRAC`/`OPDLS` state.
- ✅ **Correction:** the slot names ARE available over telnet, so no user-configured labels are needed.

## Speaker levels and distances ✅ (pushed after each Dirac slot change)
| Line | Meaning |
|---|---|
| `SSLEVFR 535` … `SSLEV END` | Channel level: 2 digits = whole dB, 3 = tenths, 50 = 0 dB (`535` = +3.5 dB, `46` = −4 dB). Sent for all 33 possible channels. |
| `SSSDEFL 0260` / `0121` | Distance **or** delay, depending on the `SSSDESTP` line that ends the block. Only sent for configured speakers, so it tells which speakers exist. |
| `SSSDESTP 01M` / `01S` | ✅ Unit marker. `01M` (Dirac Off): values are distances in cm (`0260` = 2.60 m). `01S` (Dirac filter): values are **delays in 0.1 ms** (`0121` = 12.1 ms). Verified against the receiver's settings print (16 Nov 2026): sub 0.0 ms, other channels 10.9–13.3 ms, same pattern as the telnet values (sub `0000`, SL largest, heights smallest). |
| `SS2DSSDEFL 0121`, `SS2DSCLVFL 52` | Same for FL/FR in a second ("2DS") block, probably the 2-channel/Direct set. Not used yet. |
| `SSTTL*` | Test tone levels. Not used. |

Dirac delays: the sub is the 0 ms reference (its own latency), so the common ~12 ms offset is not
distance. Only the differences matter: a larger delay = acoustically closer, 1 ms ≈ 0.343 m. HA shows
this as `relative_acoustic_distance_m` on the delay sensors (vs the channel with the largest delay,
subs left out).

Crossovers / speaker sizes: not seen. Queries to try in the second probe (`--set speakers`).
Expected values from Markus's settings print (16 Nov 2026), to decode the probe's replies:

| Setting | Value |
|---|---|
| Front | Full Range |
| Center | 60 Hz |
| Surround | 100 Hz |
| Surround Back | 70 Hz |
| Heights | 100 Hz |
| Subwoofer output | LFE + Main |
| LFE LPF | 80 Hz |
| Bass Extraction LPF | 80 Hz (multichannel) / 40 Hz (2ch) |
| Subwoofer level adjust | −3.5 dB (set by Dirac) |

Note: these are from before the 20 Nov changes (new sub position and Dirac run), so the crossovers may
have changed since.

## Signal / format info ✅ (all pushed as events)
| Line | Meaning |
|---|---|
| `MSDOLBY ATMOS`, `MSDOLBY AUDIO-DD+`, `MSDOLBY AUDIO-DSUR`, `MSMULTI CH IN`, `MSSTEREO` | Sound mode (raw) |
| `SYSMI Dolby Atmos` / `SYSMI Multi Ch In` | Human-readable sound mode |
| `SYSDA Dolby Atmos` / `SYSDA PCM` / `SYSDA Unknown` | Input audio format (space-padded) |
| `SSINFAISSIG 25` | Signal code: 02=PCM, 04=DD+, 12=none/analog?, 25=Atmos (map more as seen) |
| `SSINFAISFSV 48K` / `441` / `NON` | Sample rate (`441` = 44.1 kHz) |
| `OPINFASP 2222…` / `OPINFINS 1111…` | Per-channel bitmaps (active speakers / input channels); decode later |
| `SSSMG MOV`/`MUS` | Smart Select group (movie/music/game) |
| `OPSMLALL MOV021Dolby Atmos` … `OPSMLALL END` | Available sound modes list. The 3rd digit `1` marks the currently selected one |
| `MSSMART0` | Smart Select slot |

## Other settings ✅
`PSMULTEQ:OFF` (Audyssey off, as expected with Dirac), `PSDYNEQ OFF`, `PSREFLEV 0`, `PSDYNVOL OFF`,
`PSDRC OFF`, `PSLFE 00`, `PSBAS 50`, `PSTRE 50`, `PSTONE CTRL OFF`, `PSDELAY 162` (per input),
`PSLFC OFF`, `PSCNTAMT 04`, `PSGEQ OFF`, `PSHEQ OFF`, `PSSURLEV HEV`, `PSMDAX OFF`, `PSSWL 46`
(sub level), `SPPR 2` (speaker preset), `DIM DAR`, `VSMONI1`, `VSSCHAUTO`/`VSVPMAUTO`, `SDAUTO`,
`DCAUTO`, `CVTTR ON` / `CVTTR 50` (tactile), `CVFL 50`… `CVEND` (channel volumes), `SLPOFF`,
`MV225`, `MUON`/`MUOFF`, `MNMEN ON/OFF` (setup menu open/closed), `SSFUN<code> <name>` (input
renames), `SSHOS*` (HDMI/CEC settings), `SSPTSLSTHD*` (HDMI input assignments).

## No reply on AV 20 ❌
`CV?` (no direct reply, but CV lines arrive as events), `PSRSZ ?`, `PSRSTR ?`, `ECO?`.

## Quirks
- `MVMAX` flips between values (`98`, `895`, `93`, `865`) constantly, so don't treat it as meaningful state.
- Lines arrive in bursts of 100+ lines. The parser must be line-buffered on `\r` and handle padding.

## Still to verify
- A query command for the OPDLS block (try `OPDLS ?`, `OPDLSSL ?`)
- More `SSINFAISSIG` codes (DTS, DTS:X, TrueHD, PCM 2ch vs multich)
- Other `OPDLSSL*TYP` values (filter without ART)
