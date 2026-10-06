import unittest,tempfile,json
from pathlib import Path
from quality_core import paired_frames,split_depth_groups,StageLedger

class ProtocolTests(unittest.TestCase):
 def test_one_to_one_sync_does_not_reuse_depth(self):
  p=paired_frames([1.,1.01,1.04],[1.005,1.04],.02)
  self.assertEqual(len(p),2);self.assertEqual(len({j for i,j in p}),2)
  self.assertTrue(all(abs([1.,1.01,1.04][i]-[1.005,1.04][j])<=.02 for i,j in p))
 def test_sync_rejects_out_of_window(self):
  self.assertEqual(paired_frames([1,2],[1.03,2.04],.02),[])
 def test_shared_test_depth_is_removed_from_training(self):
  rows=[dict(source_frame=i,depth_id=d) for i,d in enumerate(['a','b','b','c','d'])]
  train,test=split_depth_groups(rows,{2})
  self.assertEqual([x['source_frame'] for x in train],[0,3,4])
  self.assertEqual({x['depth_id'] for x in train}&{x['depth_id'] for x in test},set())
 def test_resume_rejects_protocol_change(self):
  with tempfile.TemporaryDirectory() as t:
   l=StageLedger(Path(t)/'state.json','v1');l.finish('a',{'exit':0});self.assertTrue(StageLedger(Path(t)/'state.json','v1').done('a'))
   with self.assertRaises(ValueError):StageLedger(Path(t)/'state.json','v2')
 def test_failed_stage_never_counts_done(self):
  with tempfile.TemporaryDirectory() as t:
   l=StageLedger(Path(t)/'state.json','v1');l.fail('a','OOM');self.assertFalse(l.done('a'))

if __name__=='__main__':unittest.main()
