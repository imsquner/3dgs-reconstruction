import unittest,tempfile,json,copy
from pathlib import Path
from quality_core import sha256
from portable_protocol import rebase_protocol,semantic_hash,verify_observations

class PortableProtocolTests(unittest.TestCase):
 def protocol(self):
  row={'source_frame':7,'rgb_path':'/old/data/rgb/a.png','depth_path':'/old/data/depth/b.png','depth_id':'depth/b.png','reference_c2w':[[1,0],[0,1]],'rgb_timestamp':3.2}
  return {'source':'/old/data','scene':'fixture','intrinsic':[1,2,3,4],'file_hashes':{},'upstream_original_train':[row],'upstream_original_validation':[]}
 def test_only_runtime_paths_change_and_semantics_remain(self):
  old=self.protocol();snapshot=copy.deepcopy(old);new=rebase_protocol(old,'/new/data')
  self.assertEqual(old,snapshot);self.assertEqual(new['upstream_original_train'][0]['depth_id'],'depth/b.png')
  self.assertEqual(new['upstream_original_train'][0]['reference_c2w'],old['upstream_original_train'][0]['reference_c2w'])
  self.assertEqual(new['upstream_original_train'][0]['rgb_path'],str(Path('/new/data').resolve()/'rgb/a.png'))
  self.assertEqual(semantic_hash(old),semantic_hash(new))
 def test_windows_paths_preserve_platform_independent_semantics(self):
  old=self.protocol();windows=copy.deepcopy(old);windows['source']='C:\\datasets\\fixture'
  windows['upstream_original_train'][0]['rgb_path']='C:\\datasets\\fixture\\rgb\\a.png'
  windows['upstream_original_train'][0]['depth_path']='C:\\datasets\\fixture\\depth\\b.png'
  self.assertEqual(semantic_hash(old),semantic_hash(windows))
  windows['upstream_original_train'][0]['depth_path']='C:\\datasets\\fixture\\..\\outside.png'
  with self.assertRaises(ValueError):semantic_hash(windows)
 def test_wrong_dataset_or_path_escape_is_rejected(self):
  old=self.protocol();old['upstream_original_train'][0]['rgb_path']='/other/data/a.png'
  with self.assertRaises(ValueError):rebase_protocol(old,'/new/data')
  old=self.protocol();old['upstream_original_train'][0]['depth_path']='/old/data/../outside.png'
  with self.assertRaises(ValueError):rebase_protocol(old,'/new/data')
 def test_real_content_is_verified_not_just_file_presence(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'rgb').mkdir();(root/'depth').mkdir();f=root/'rgb/a.png';f.write_bytes(b'original-observation');depth=root/'depth/b.png';depth.write_bytes(b'depth-observation')
   obs={'complete':True,'files':{old:{'bytes':p.stat().st_size,'sha256':sha256(p)} for old,p in [('/old/data/rgb/a.png',f),('/old/data/depth/b.png',depth)]}}
   self.assertEqual(len(verify_observations(self.protocol(),obs,root)),2)
   f.write_bytes(b'X'*f.stat().st_size)
   with self.assertRaises(ValueError):verify_observations(self.protocol(),obs,root)
 def test_complete_flag_does_not_replace_manifest_coverage(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'rgb').mkdir();f=root/'rgb/a.png';f.write_bytes(b'original-observation')
   obs={'complete':True,'files':{'/old/data/rgb/a.png':{'bytes':f.stat().st_size,'sha256':sha256(f)}}}
   with self.assertRaises(ValueError):verify_observations(self.protocol(),obs,root)

if __name__=='__main__':unittest.main()
