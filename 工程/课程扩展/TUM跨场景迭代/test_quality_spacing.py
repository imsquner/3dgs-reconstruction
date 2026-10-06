import unittest
import torch
from quality_spacing import install_spacing_tracking

class SpacingTests(unittest.TestCase):
 def test_create_add_prune_preserves_birth_spacing(self):
  class Fake:
   @property
   def get_scaling(self):return self.scales
   def create_from_pcd2_tensor(self,scales):self.scales=scales.clone()
   def add_from_pcd2_tensor(self,scales):self.scales=torch.cat([self.scales,scales])
   def prune_points(self,mask):self.scales=self.scales[~mask]
  install_spacing_tracking(Fake);model=Fake()
  model.create_from_pcd2_tensor(torch.tensor([[3.,2.,1.],[6.,4.,2.]]))
  model.scales*=10 # Learned growth must not overwrite the birth reference.
  model.add_from_pcd2_tensor(torch.tensor([[9.,8.,7.]]))
  self.assertTrue(torch.equal(model.quality_initial_spacing,torch.tensor([2.,4.,8.])))
  model.prune_points(torch.tensor([False,True,False]))
  self.assertTrue(torch.equal(model.quality_initial_spacing,torch.tensor([2.,8.])))
  self.assertEqual(len(model.get_scaling),len(model.quality_initial_spacing))

 def test_install_twice_is_idempotent(self):
  class Fake:
   @property
   def get_scaling(self):return self.scales
   def create_from_pcd2_tensor(self,x):self.scales=x
   def add_from_pcd2_tensor(self,x):self.scales=torch.cat([self.scales,x])
   def prune_points(self,mask):self.scales=self.scales[~mask]
  install_spacing_tracking(Fake);method=Fake.add_from_pcd2_tensor
  install_spacing_tracking(Fake)
  self.assertIs(method,Fake.add_from_pcd2_tensor)

if __name__=='__main__':unittest.main()
