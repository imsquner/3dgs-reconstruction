#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试渐进建图：对每个模型在不同时间点取帧，看 born 是否随时间增长。"""
import asyncio
import json
import os

import websockets

URL = "ws://127.0.0.1:8771"
OUT = "/mnt/d/Temp/grow_test"


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with websockets.connect(URL, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "hello"}))
        scene = json.loads(await ws.recv())
        print("models:", scene.get("models"), "current:", scene.get("name"))

        for name in scene.get("models", []):
            await ws.send(json.dumps({"type": "use", "name": name}))
            while True:
                h = json.loads(await ws.recv())
                if h.get("type") in ("scene", "error"):
                    break
            if h.get("type") == "error":
                print(name, "切换失败", h); continue

            print(f"--- {name} ---")
            for t in (0.0, 0.25, 0.5, 0.75, 0.99):
                await ws.send(json.dumps({"t": t, "mode": "free", "w": 640, "h": 480,
                                          "q": 85, "grow": True}))
                hdr = json.loads(await ws.recv())
                data = await ws.recv()
                born = hdr.get("born")
                total = hdr.get("total")
                tag = f"{born}/{total}" if born is not None else "无出生数据"
                print(f"  t={t:.2f} idx={hdr['idx']:3d} {tag}  {hdr['ms']:.1f} ms")
                if t in (0.0, 0.99):
                    open(os.path.join(OUT, f"{name}_t{int(t*100):02d}.jpg"), "wb").write(data)


asyncio.run(main())
