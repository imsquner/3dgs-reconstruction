#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比渐进建图开/关在不同时间的画面。"""
import asyncio
import json
import os

import websockets

URL = "ws://127.0.0.1:8771"
OUT = "/mnt/d/Temp/grow_cmp"


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with websockets.connect(URL, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "hello"}))
        scene = json.loads(await ws.recv())
        print("models:", scene.get("models"), "current:", scene.get("name"))
        if scene.get("name") != "grow_static":
            await ws.send(json.dumps({"type": "use", "name": "grow_static"}))
            while True:
                h = json.loads(await ws.recv())
                if h.get("type") in ("scene", "error"):
                    break
            print("switched:", h.get("name"))

        for tag, grow in (("full", False), ("grow", True)):
            for t in (0.0, 0.3, 0.6, 0.99):
                await ws.send(json.dumps({"t": t, "mode": "free", "w": 640, "h": 480,
                                          "q": 88, "grow": grow}))
                hdr = json.loads(await ws.recv())
                data = await ws.recv()
                born = hdr.get("born")
                total = hdr.get("total")
                name = f"{tag}_t{int(t*100):02d}.jpg"
                open(os.path.join(OUT, name), "wb").write(data)
                print(f"{name}: idx={hdr['idx']:3d} born={born}/{total} {hdr['ms']:.1f} ms")


asyncio.run(main())
