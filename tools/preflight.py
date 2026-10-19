"""Read-only checks. CPU mode checks repository; --gpu checks runtime readiness."""
import argparse
import importlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / '工程/交互演示'
SCENES = (
    DEMO / 'assets/replica.json',
    DEMO / 'assets/natural/tum-comparison/GSICP10.json',
    DEMO / 'assets/natural/ooosplat-office/balanced/scene.json',
    DEMO / 'assets/medical/tsdf/trans_t2_b/open3d_park_v0500/scene.json',
    DEMO / 'assets/medical/tsdf/cecum_t1_a/open3d_park_v1000/scene.json',
)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gpu', action='store_true')
    a = p.parse_args()
    failures = []
    def check(label, condition):
        print(('PASS ' if condition else 'FAIL ') + label, flush=True)
        if not condition:
            failures.append(label)
    check('Python >= 3.10 (CPU tooling)', sys.version_info >= (3, 10))
    check('demo site sources', all((DEMO / n).is_file() for n in ('server.py', 'catalog.mjs', 'app.mjs')))
    check('public scene protocols', all(path.is_file() for path in SCENES))
    for path in SCENES:
        try:
            scene = json.loads(path.read_text(encoding='utf-8'))
            check('valid scene ' + path.parent.name, bool(scene.get('ply')) and 'intrinsic' in scene)
        except (ValueError, OSError):
            check('valid scene ' + path.parent.name, False)
    if a.gpu:
        check('Linux runtime', platform.system() == 'Linux')
        check('Python 3.10 target', sys.version_info[:2] == (3, 10))
        check('upstream setup tool present', (ROOT / 'tools/setup_upstream.py').is_file())
        for name in ('nvidia-smi', 'nvcc'):
            executable = shutil.which(name)
            check(name + ' available', executable is not None)
            if executable:
                args = ['--query-gpu=name,driver_version', '--format=csv,noheader'] if name == 'nvidia-smi' else ['--version']
                result = subprocess.run([executable] + args, capture_output=True, text=True, timeout=30)
                check(name + ' succeeds', result.returncode == 0)
                print(result.stdout.strip(), flush=True)
                if name == 'nvcc':
                    check('nvcc 11.6 target', 'release 11.6' in result.stdout)
        for name in ('torch', 'numpy', 'cv2', 'open3d', 'torchmetrics', 'rerun', 'pygicp', 'simple_knn._C', 'diff_gaussian_rasterization._C'):
            try:
                module = importlib.import_module(name)
                check('import ' + name, True)
                if name == 'torch':
                    check('torch 1.12.1+cu116 target', module.__version__ == '1.12.1+cu116')
                    check('Torch CUDA available', module.cuda.is_available())
                if name == 'numpy':
                    check('numpy 1.23.5 target', module.__version__ == '1.23.5')
            except Exception as error:
                check('import ' + name + ' (' + type(error).__name__ + ')', False)
    print('PREFLIGHT', 'FAILED' if failures else 'OK', 'failures=' + str(len(failures)), flush=True)
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
