#!/usr/bin/env python3
"""Read-only telnet probe for Denon/Marantz AVRs.

Sends a list of '?' status queries, then listens for events and logs every line
with a timestamp to captures/.

IMPORTANT: the receiver allows only ONE telnet connection. Disable the Home
Assistant denonavr integration (or its telnet option) before running this.

Usage:
    python tools/telnet_probe.py 192.168.1.50 --listen 120 --note dirac-test
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from pathlib import Path

# Read-only queries only. Never add commands that change state here.
QUERIES = [
    "PW?", "ZM?", "SI?", "MS?", "MV?", "CV?",
    "PSDIRAC ?",
    "PSDYNEQ ?", "PSREFLEV ?", "PSDYNVOL ?", "PSLFE ?",
    "PSBAS ?", "PSTRE ?", "PSTONE CTRL ?", "PSDRC ?",
    "PSDELAY ?", "PSRSZ ?", "PSRSTR ?",
    "SPPR ?", "ECO?", "DIM ?", "VSMONI ?",
    "SSINFAISFSV ?", "SSINFAISSIG ?", "MSSMART ?",
]


async def probe(host: str, port: int, listen: float, delay: float, out: Path) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    start = dt.datetime.now()

    with out.open("w", encoding="utf-8") as log:
        def emit(kind: str, text: str) -> None:
            t = (dt.datetime.now() - start).total_seconds()
            line = f"{t:8.3f} {kind} {text}"
            print(line)
            log.write(line + "\n")
            log.flush()

        async def read_loop() -> None:
            buf = b""
            while True:
                chunk = await reader.read(1024)
                if not chunk:
                    emit("!!", "connection closed")
                    return
                buf += chunk
                while b"\r" in buf:
                    raw, buf = buf.split(b"\r", 1)
                    if raw.strip():
                        emit("<<", raw.decode("ascii", errors="replace"))

        reader_task = asyncio.create_task(read_loop())

        for q in QUERIES:
            emit(">>", q)
            writer.write((q + "\r").encode("ascii"))
            await writer.drain()
            await asyncio.sleep(delay)

        emit("--", f"queries done; listening {listen:.0f}s for events "
                   "(change input / Dirac slot / sound mode on the remote now)")
        try:
            await asyncio.wait_for(reader_task, timeout=listen)
        except asyncio.TimeoutError:
            pass
        writer.close()
        await writer.wait_closed()
        emit("--", "done")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("--port", type=int, default=23)
    p.add_argument("--listen", type=float, default=60, help="seconds to listen for events after queries")
    p.add_argument("--delay", type=float, default=0.3, help="seconds between queries")
    p.add_argument("--note", default="probe", help="suffix for the capture file name")
    a = p.parse_args()

    captures = Path(__file__).resolve().parent.parent / "captures"
    captures.mkdir(exist_ok=True)
    out = captures / f"{dt.datetime.now():%Y%m%d-%H%M}-{a.note}.log"
    print(f"Logging to {out}")
    asyncio.run(probe(a.host, a.port, a.listen, a.delay, out))


if __name__ == "__main__":
    main()
