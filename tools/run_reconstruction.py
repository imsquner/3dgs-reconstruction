"""Small baseline smoke run. Every invocation preserves a unique output directory."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '工程/课程扩展/TUM跨场景迭代'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--frames', type=int, default=2)
    p.add_argument('--steps-per-frame', type=int, default=10)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--run-id')
    a = p.parse_args()
    if a.frames < 2 or a.steps_per_frame < 1:
        p.error('frames must be >= 2 and steps-per-frame >= 1')
    if not a.protocol.is_file():
        p.error('protocol file is missing; run prepare_dataset.py first')
    protocol = json.loads(a.protocol.read_text(encoding='utf-8'))
    rows = protocol['upstream_original_train']
    if len(rows) < a.frames:
        p.error('protocol has fewer training frames than requested')
    for row in rows[:a.frames]:
        for field in ('rgb_path', 'depth_path'):
            if not Path(row[field]).is_file():
                p.error('missing observation: ' + row[field])
    run_id = a.run_id or ('smoke-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    if Path(run_id).name != run_id or run_id in ('.', '..'):
        p.error('run-id must be a plain directory name')
    if (ROOT / '工程/运行' / run_id).exists():
        p.error('run output already exists; choose another run-id')
    check = subprocess.call([sys.executable, str(ROOT / 'tools/preflight.py'), '--gpu'])
    if check:
        return check
    command = [sys.executable, '-u', str(STAGE / 'run_online_v18.py'), '--protocol', str(a.protocol.resolve()),
        '--scene', protocol['scene'], '--run-id', run_id, '--frames', str(a.frames),
        '--steps-per-frame', str(a.steps_per_frame), '--seed', str(a.seed),
        '--variant', 'original', '--pose-prior', 'previous', '--association', 'original']
    print('RUN_ID', run_id, 'OUTPUT', ROOT / '工程/运行' / run_id, flush=True)
    return subprocess.call(command)

if __name__ == '__main__':
    raise SystemExit(main())
