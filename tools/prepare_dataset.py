"""Verify downloaded observations and materialize paths; never regenerate holdouts."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '工程/课程扩展/TUM跨场景迭代'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if Path(args.scene).name != args.scene or args.scene in ('.', '..'):
        parser.error('scene must be a plain scene name')
    protocol = STAGE / '协议' / (args.scene + '.json')
    observations = STAGE / '协议' / (args.scene + '-observations.json')
    for path in (protocol, observations):
        if not path.is_file():
            parser.error('missing canonical input: ' + str(path))
    if not args.dataset_root.is_dir():
        parser.error('dataset-root must be an extracted dataset directory')
    output = args.output_dir.resolve()
    frozen = (STAGE / '协议').resolve()
    if output == frozen or frozen in output.parents:
        parser.error('output-dir must be outside frozen protocols')
    if output.exists() and any(output.iterdir()):
        parser.error('use a new empty output directory; existing output is preserved')
    return subprocess.call([sys.executable, '-u', str(STAGE / 'portable_protocol.py'),
        '--protocol', str(protocol), '--observations', str(observations),
        '--dataset-root', str(args.dataset_root.resolve()), '--output-dir', str(output)])

if __name__ == '__main__':
    raise SystemExit(main())
