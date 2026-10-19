#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试演示动画模式在不同时间的稀疏程度。"""
import asyncio
import json
import os

import websockets

URL = "ws://127.0.0.1:8771"
OUT = "/mnt/d/Temp/anim_test"


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with websockets.connect(URL, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "hello"}))
        await ws.recv()
        for t in (0.0, 0.1, 0.2, 0.35, 0.5, 0.99):
            await ws.send(json.dumps({"t": t, "mode": "free", "w": 640, "h": 480,
                                      "q": 88, "anim": True}))
            hdr = json.loads(await ws.recv())
            data = await ws.recv()
            name = f"anim_t{int(t*100):02d}.jpg"
            open(os.path.join(OUT, name), "wb").write(data)
            print(f"{name}: idx={hdr['idx']:3d} 显示 {hdr['born']}/{hdr['total']}  {hdr['ms']:.1f} ms")


asyncio.run(main())
