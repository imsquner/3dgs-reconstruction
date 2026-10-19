#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页渲染服务的自测：连上 WS，取 3 帧，验证 JPEG 与非空渲染。"""
import asyncio
import json

import websockets

URL = "ws://127.0.0.1:8771"


async def main():
    async with websockets.connect(URL, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "hello"}))
        scene = json.loads(await ws.recv())
        print("scene:", scene)

        for i, (t, yaw, pitch, dist) in enumerate([(0.0, 0, 8, None), (0.5, 20, 12, None), (0.95, -15, 6, None)]):
            req = {"t": t, "yaw": yaw, "pitch": pitch, "mode": "orbit", "w": 640, "h": 480, "q": 85}
            if dist:
                req["dist"] = dist
            else:
                req["dist"] = scene["radius"] * 1.6
            await ws.send(json.dumps(req))
            hdr = json.loads(await ws.recv())
            data = await ws.recv()
            print(f"frame {i}: t={hdr['t']:.2f} idx={hdr['idx']} {hdr['w']}x{hdr['h']} "
                  f"{hdr['ms']:.1f} ms, jpeg {len(data)} bytes")
            open(f"/tmp/test_frame_{i}.jpg", "wb").write(data)

        # 轨迹模式
        await ws.send(json.dumps({"t": 0.5, "mode": "traj", "w": 960, "h": 720, "q": 90}))
        hdr = json.loads(await ws.recv())
        data = await ws.recv()
        print(f"traj frame: t={hdr['t']:.2f} idx={hdr['idx']} 960x720 {hdr['ms']:.1f} ms, {len(data)} bytes")
        open("/tmp/test_frame_traj.jpg", "wb").write(data)


asyncio.run(main())
