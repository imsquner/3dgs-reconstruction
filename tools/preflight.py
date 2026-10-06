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
STAGE = ROOT / '工程/课程扩展/TUM跨场景迭代'

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
    check('runner and portable protocol', all((STAGE / n).is_file() for n in ('run_online_v18.py', 'portable_protocol.py')))
    protocols = list((STAGE / '协议').glob('*.json'))
    check('public scene protocols', any(not x.stem.endswith(('-observations', '-host-materialization')) for x in protocols))
    for path in protocols:
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            check('valid JSON ' + path.name, False)
    if a.gpu:
        check('Linux runtime', platform.system() == 'Linux')
        check('Python 3.10 target', sys.version_info[:2] == (3, 10))
        check('pinned upstream fetched', (STAGE / '来源/GS-ICP-SLAM/gs_icp_slam.py').is_file())
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
