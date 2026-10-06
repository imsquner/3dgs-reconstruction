import tempfile,unittest
from pathlib import Path
import numpy as np,torch
from quality_selection_trace import install

def fixture(root):
 class Model:
  @property
  def get_xyz(self):return self.xyz
  @property
  def get_opacity(self):return self.opacity[:,None]
  @property
  def get_scaling(self):return torch.ones(len(self.xyz),3)
  def create_from_pcd2_tensor(self,points):
   self.xyz=points.clone();self.opacity=torch.tensor([.1,.04,.1])[:len(points)];self.trackable_mask=torch.ones(len(points),dtype=torch.bool)
  def add_from_pcd2_tensor(self,points):
   self.xyz=torch.cat([self.xyz,points]);self.opacity=torch.cat([self.opacity,torch.ones(len(points))*.1]);self.trackable_mask=torch.cat([self.trackable_mask,torch.ones(len(points),dtype=torch.bool)])
  def prune_points(self,mask):
   self.xyz=self.xyz[~mask];self.opacity=self.opacity[~mask];self.trackable_mask=self.trackable_mask[~mask]
  def get_trackable_gaussians_tensor(self,threshold):
   mask=self.trackable_mask&(self.opacity>threshold);n=int(mask.sum())
   return self.xyz[mask],torch.ones(n,4),torch.ones(n,3)
 class Mapper:
  def __init__(self,system):self.gaussians=Model();self.iter_shared=[0];self.train_iter=200
 install(Model,Mapper,root);return Mapper(None).gaussians

class Selection(unittest.TestCase):
 def test_snapshot_leaves_selection_and_opacity_unchanged(self):
  with tempfile.TemporaryDirectory() as t:
   m=fixture(t);points=torch.arange(9).reshape(3,3).float();m.create_from_pcd2_tensor(points);before=m.opacity.clone()
   result=m.get_trackable_gaussians_tensor(.05)
   self.assertTrue(torch.equal(result[0],points[[0,2]]));self.assertTrue(torch.equal(before,m.opacity))
   snap=np.load(Path(t)/'筛选输入/selection-0000.npz');self.assertEqual(snap['selected_ids'].tolist(),[0,2])
 def test_prune_and_add_keep_non_reused_insertion_ids(self):
  with tempfile.TemporaryDirectory() as t:
   m=fixture(t);m.create_from_pcd2_tensor(torch.zeros(3,3));m.prune_points(torch.tensor([False,True,False]));m.add_from_pcd2_tensor(torch.ones(2,3))
   self.assertEqual(m.quality_selection_ids.tolist(),[0,2,3,4]);m.get_trackable_gaussians_tensor(.05)
   p=np.load(Path(t)/'筛选输入/prune-0000-000200.npz');self.assertEqual(p['removed_ids'].tolist(),[1]);self.assertAlmostEqual(float(p['opacity'][0]),.04)

if __name__=='__main__':unittest.main()
