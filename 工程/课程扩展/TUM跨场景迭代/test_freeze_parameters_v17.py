import json,unittest,copy
from pathlib import Path
from freeze_parameters_v17 import from_manifest
B=Path(__file__).resolve().parent
class Parameters17(unittest.TestCase):
 def setUp(self):self.m=json.loads((B.parents[1]/'运行/local-tum-quality-motion1200-combined-b20-v17/manifest.json').read_text())
 def test_actual_motion_prior_export(self):
  p=from_manifest(self.m);self.assertEqual(p['pose_prior'],'constant-velocity');self.assertEqual(p['motion_ratio_upper_bound'],2.);self.assertEqual(p['tracking_positions'],'optimized');self.assertEqual(p['needle_weight'],.002)
 def test_changed_motion_source_rejected(self):
  self.m['quality_module_hashes']['quality_motion_prior.py']='0'*64
  with self.assertRaises(AssertionError):from_manifest(self.m)
 def test_missing_prior_rejected(self):
  del self.m['quality_args']['pose_prior']
  with self.assertRaises(AssertionError):from_manifest(self.m)
 def test_unknown_prior_rejected(self):
  self.m['quality_args']['pose_prior']='ground-truth'
  with self.assertRaises(AssertionError):from_manifest(self.m)
 def test_previous_explicit_export(self):
  self.m['quality_args']['pose_prior']='previous';p=from_manifest(self.m);self.assertEqual(p['pose_prior'],'previous');self.assertFalse(p['motion_prediction_enabled'])
if __name__=='__main__':unittest.main()
