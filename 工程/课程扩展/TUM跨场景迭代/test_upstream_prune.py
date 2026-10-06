import unittest,torch
from upstream_prune import original_prune_mask
class PruneTests(unittest.TestCase):
 def test_tum_boundary_opacity_and_size(self):
  s=torch.tensor([[1.,.1,.01],[1.01,.1,.01],[.1,.1,.1]])
  op=torch.tensor([[.5],[.5],[.004]])
  self.assertEqual(original_prune_mask(s,op,10.).tolist(),[False,True,True])
 def test_replica_original_extent(self):
  s=torch.tensor([[.25,.1,.01],[.251,.1,.01]])
  self.assertEqual(original_prune_mask(s,torch.ones(2,1),2.5).tolist(),[False,True])
if __name__=='__main__':unittest.main()
