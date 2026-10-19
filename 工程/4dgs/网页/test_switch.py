#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试多模型切换：列出模型 -> 切到指定模型 -> 渲染一帧。"""
import asyncio
import json
import os
import sys

import websockets

URL = "ws://127.0.0.1:8771"
OUT = "/mnt/d/Temp/switch_test"


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
                if h.get("type") == "scene":
                    break
                if h.get("type") == "error":
                    print("error:", h)
                    break
            print(f"切换 -> {h.get('name')}  帧={h.get('frames')} 高斯={h.get('gaussians')} 关键帧={h.get('keyframes')}")

            await ws.send(json.dumps({"t": 0.5, "mode": "free", "w": 640, "h": 480, "q": 85}))
            hdr = json.loads(await ws.recv())
            data = await ws.recv()
            open(os.path.join(OUT, f"{name}.jpg"), "wb").write(data)
            print(f"   渲染帧 {len(data)} bytes, {hdr['ms']:.1f} ms")


asyncio.run(main())
