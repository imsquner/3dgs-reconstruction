#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「原机位小幅观察」：yaw/pitch/dolly 三个方向各取极值，看是否仍然合理。"""
import asyncio
import json
import os

import websockets

URL = "ws://127.0.0.1:8771"
OUT = "/mnt/d/Temp/free_test"


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with websockets.connect(URL, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "hello"}))
        await ws.recv()
        cases = [
            ("t148_base", 0.5, 0, 0, 0),
            ("t148_yaw+35", 0.5, 35, 0, 0),
            ("t148_yaw-35", 0.5, -35, 0, 0),
            ("t148_pitch+25", 0.5, 0, 25, 0),
            ("t148_dolly+0.5", 0.5, 0, 0, 0.5),
            ("t148_combo", 0.5, 20, 12, 0.3),
            ("t0_traj", 0.0, 0, 0, 0),
        ]
        for name, t, yaw, pitch, dolly in cases:
            await ws.send(json.dumps({"t": t, "yaw": yaw, "pitch": pitch, "dolly": dolly,
                                      "mode": "free", "w": 640, "h": 480, "q": 85}))
            hdr = json.loads(await ws.recv())
            data = await ws.recv()
            open(os.path.join(OUT, f"{name}.jpg"), "wb").write(data)
            print(f"{name:16s} idx={hdr['idx']:3d} {hdr['ms']:6.1f} ms  {len(data):7d} bytes")


asyncio.run(main())
