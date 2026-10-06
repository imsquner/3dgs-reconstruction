import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import prepare_dataset

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '工程/课程扩展/TUM跨场景迭代'

class RuntimeCliTests(unittest.TestCase):
    def test_missing_required_arguments(self):
        for name in ('prepare_dataset.py', 'run_reconstruction.py'):
            self.assertNotEqual(subprocess.run([sys.executable, str(ROOT/'tools'/name)], capture_output=True).returncode, 0)

    def test_missing_protocol_rejected_before_gpu(self):
        result = subprocess.run([sys.executable, str(ROOT/'tools/run_reconstruction.py'), '--protocol', 'does-not-exist.json'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('protocol file is missing', result.stderr)

    def test_runner_uses_actual_protocol_and_preserves_default(self):
        source = (STAGE/'run_online_v18.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("a.protocol is not None else B/'协议'/f'{a.scene}.json'", source)
        self.assertIn('protocol_path=str(PROTOCOL_PATH),protocol_sha256=sha256(PROTOCOL_PATH)', source)

    def test_prepare_refuses_frozen_output(self):
        # Invalid output is rejected before any observation materialization.
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT/'tools/prepare_dataset.py'), '--scene', '../escape', '--dataset-root', directory, '--output-dir', directory], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('plain scene name', result.stderr)

    def test_prepare_preserves_existing_output_and_frozen_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root/'stage'
            frozen = stage/'协议'
            frozen.mkdir(parents=True)
            (frozen/'fixture.json').write_text('{}')
            (frozen/'fixture-observations.json').write_text('{}')
            existing = root/'existing'
            existing.mkdir()
            sentinel = existing/'saved.txt'
            sentinel.write_text('preserve')
            for output in (existing, frozen):
                args = ['prepare_dataset.py', '--scene', 'fixture', '--dataset-root', str(root), '--output-dir', str(output)]
                with patch.object(prepare_dataset, 'STAGE', stage), patch.object(sys, 'argv', args):
                    with self.assertRaises(SystemExit) as result:
                        prepare_dataset.main()
                    self.assertEqual(result.exception.code, 2)
            self.assertEqual(sentinel.read_text(), 'preserve')

if __name__ == '__main__':
    unittest.main()
