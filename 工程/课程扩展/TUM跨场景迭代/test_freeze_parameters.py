import copy,json,unittest
from freeze_parameters import from_manifest,B
class Parameters(unittest.TestCase):
 def setUp(self):self.manifest=json.loads((B.parents[1]/'运行/local-tum-quality-feedback240-optimizedxyz-b20-v16/manifest.json').read_text())
 def test_actual_manifest_without_factor(self):
  self.assertNotIn('growth_factor',self.manifest['quality_args']);p=from_manifest(self.manifest)
  self.assertEqual(p['growth_factor'],8.);self.assertEqual(p['needle_weight'],.002);self.assertEqual(p['tracking_positions'],'optimized');self.assertEqual(p['tracking_opacity'],'birth')
 def test_reject_changed_growth_source(self):
  self.manifest['quality_module_hashes']['quality_growth.py']='0'*64
  with self.assertRaises(AssertionError):from_manifest(self.manifest)
 def test_reject_conflicting_explicit_factor(self):
  self.manifest['quality_args']['growth_factor']=4.
  with self.assertRaises(AssertionError):from_manifest(self.manifest)
 def test_reject_missing_required_parameter(self):
  self.manifest['quality_args'].pop('tracking_opacity')
  with self.assertRaises(AssertionError):from_manifest(self.manifest)
 def test_reject_changed_loss_source(self):
  self.manifest['quality_module_hashes']['online_quality_patch_v3.py']='0'*64
  with self.assertRaises(AssertionError):from_manifest(self.manifest)
 def test_reject_conflicting_explicit_needle(self):
  self.manifest['quality_args']['needle_weight']=.005
  with self.assertRaises(AssertionError):from_manifest(self.manifest)
if __name__=='__main__':unittest.main()
