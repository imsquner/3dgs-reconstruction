import unittest,json,tempfile,os
from pathlib import Path
from unittest.mock import patch
from quality_core import atomic_json

class AtomicRetryTests(unittest.TestCase):
 def test_transient_reader_lock_is_retried(self):
  with tempfile.TemporaryDirectory() as directory:
   target=Path(directory)/'state.json';atomic_json(target,{'old':True});real_replace=os.replace;calls=[]
   def locked_then_replace(source,dest):
    calls.append(1)
    if len(calls)<3:raise PermissionError('simulated Windows reader lock')
    real_replace(source,dest)
   with patch('quality_core.os.replace',side_effect=locked_then_replace),patch('quality_core.time.sleep'):
    atomic_json(target,{'new':True})
   self.assertEqual(json.loads(target.read_text()),{'new':True});self.assertEqual(len(calls),3)
   self.assertFalse(target.with_suffix('.json.partial').exists())
 def test_persistent_lock_preserves_last_complete_state(self):
  with tempfile.TemporaryDirectory() as directory:
   target=Path(directory)/'state.json';atomic_json(target,{'old':True})
   with patch('quality_core.os.replace',side_effect=PermissionError('persistent lock')),patch('quality_core.time.sleep'):
    with self.assertRaises(PermissionError):atomic_json(target,{'new':True})
   self.assertEqual(json.loads(target.read_text()),{'old':True})
   self.assertEqual(json.loads(target.with_suffix('.json.partial').read_text()),{'new':True})

if __name__=='__main__':unittest.main()
