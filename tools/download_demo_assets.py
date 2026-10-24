"""Download the five demo meshes from the GitHub Release (stdlib only).

Usage:
    python tools/download_demo_assets.py            # download + verify
    python tools/download_demo_assets.py --check    # verify only
    python tools/download_demo_assets.py --dry-run  # print what would happen
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.2.0-demo-assets'
BASE = f'https://github.com/imsquner/3dgs-reconstruction/releases/download/{TAG}/'

ASSETS = [
    {
        'id': 'replica',
        'name': 'replica-web.ply',
        'dest': '工程/交互演示/assets/replica-web.ply',
        'bytes': 77977445,
        'sha256': '99ad4eaa2f3810fbab68106ce84165054000ed4c9b84897b6a73fb18555f1c7f',
    },
    {
        'id': 'tum-gsicp10',
        'name': 'GSICP10-web.ply',
        'dest': '工程/交互演示/assets/natural/tum-comparison/GSICP10-web.ply',
        'bytes': 32979736,
        'sha256': '9828c8b9527f4b3f16ff1a53c826dc466c00f899b93f1d707d34a9e58b74b4af',
    },
    {
        'id': 'ooosplat',
        'name': 'ooosplat-final.ply',
        'dest': '工程/交互演示/assets/natural/ooosplat-office/balanced/final.ply',
        'bytes': 118130001,
        'sha256': '3204933a45fca3ca3c4b4543514814b65e742a0ed5ec3a1cca69eea4305e2070',
    },
    {
        'id': 'c3vd-trans_t2_b',
        'name': 'c3vd-trans_t2_b-park_v0500.ply',
        'dest': '工程/交互演示/assets/medical/tsdf/trans_t2_b/open3d_park_v0500/mesh_m.ply',
        'bytes': 5596145,
        'sha256': '7528e384ed378452a2202d399f2e2757a9777a964e1f14028540703baa3710b9',
    },
    {
        'id': 'c3vd-cecum_t1_a',
        'name': 'c3vd-cecum_t1_a-park_v1000.ply',
        'dest': '工程/交互演示/assets/medical/tsdf/cecum_t1_a/open3d_park_v1000/mesh_m.ply',
        'bytes': 1994459,
        'sha256': '5c9345d54307cc5fb99d41b5a4b35cae155bc4a47e702ab8beffbdaf8fc5d4dd',
    },
]


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def ok(path, item):
    return path.is_file() and path.stat().st_size == item['bytes'] and digest(path) == item['sha256']


def download(item, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if ok(dest, item):
            print(f"{item['id']}: already present")
            return True
        raise SystemExit(f"{item['id']}: existing file does not match the manifest; remove it first")
    part = dest.with_name(dest.name + '.part')
    url = BASE + item['name']
    if part.exists() and part.stat().st_size > item['bytes']:
        part.unlink()
    start = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={'Range': f'bytes={start}-'} if start else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            if start and response.status == 206:
                mode = 'ab'
            else:
                start = 0
                mode = 'wb'
            total = start
            began = time.monotonic()
            with open(part, mode) as out:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
                    total += len(chunk)
                    if total > item['bytes']:
                        raise SystemExit(f"{item['id']}: download exceeds declared size")
                    if time.monotonic() - began >= 3:
                        rate = (total - start) / max(time.monotonic() - began, 0.001)
                        eta = (item['bytes'] - total) / max(rate, 1)
                        print(f"{item['id']}: {total}/{item['bytes']} bytes ETA {eta:.0f}s", flush=True)
                        began = time.monotonic()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{item['id']}: HTTP {error.code} for {url}")
    if part.stat().st_size != item['bytes']:
        raise SystemExit(f"{item['id']}: size mismatch, rerun to resume")
    if digest(part) != item['sha256']:
        bad = part.with_suffix('.bad')
        os.replace(part, bad)
        raise SystemExit(f"{item['id']}: sha256 mismatch, kept {bad}")
    os.replace(part, dest)
    print(f"{item['id']}: ok")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    missing = 0
    for item in ASSETS:
        dest = ROOT / item['dest']
        if args.check:
            state = 'ok' if ok(dest, item) else 'missing'
            print(f"{item['id']}: {state} -> {item['dest']}")
            missing += state != 'ok'
            continue
        if args.dry_run:
            print(f"{item['id']}: would fetch {BASE + item['name']} -> {item['dest']}")
            continue
        if not ok(dest, item):
            download(item, dest)
    if args.check and missing:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
