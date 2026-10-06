import unittest,torch
from quality_growth import growth_regularizer,install_birth_scale_tracking

class Model:
 def __init__(self):self.scales=torch.empty(0,3)
 @property
 def get_scaling(self):return self.scales
 def create_from_pcd2_tensor(self,x):self.scales=x.clone()
 def add_from_pcd2_tensor(self,x):self.scales=torch.cat([self.scales,x])
 def prune_points(self,mask):self.scales=self.scales[~mask]

class Growth(unittest.TestCase):
 def test_valid_flat_surface_is_not_penalized_for_anisotropy(self):
  birth=torch.tensor([[.2,.15,.0001]])
  self.assertEqual(float(growth_regularizer(birth,birth)),0.)
 def test_only_excess_growth_produces_gradient(self):
  birth=torch.tensor([[.01,.005,.001],[.1,.08,.0001]])
  current=torch.tensor([[.16,.1,.001],[.2,.1,.0001]],requires_grad=True)
  loss=growth_regularizer(current,birth);self.assertGreater(float(loss),0);loss.backward()
  self.assertGreater(float(current.grad[0,:2].sum()),0.)
  self.assertEqual(float(current.grad[1].abs().sum()),0.)
 def test_references_survive_growth_addition_and_pruning(self):
  install_birth_scale_tracking(Model);install_birth_scale_tracking(Model)
  m=Model();m.create_from_pcd2_tensor(torch.tensor([[.01,.02,.03]]));old=m.quality_birth_scales.clone()
  m.scales*=20;m.add_from_pcd2_tensor(torch.tensor([[.1,.2,.3]]))
  self.assertTrue(torch.equal(m.quality_birth_scales[:1],old))
  m.prune_points(torch.tensor([True,False]));self.assertTrue(torch.equal(m.quality_birth_scales,torch.tensor([[.1,.2,.3]])))
 def test_composes_with_existing_middle_spacing_tracker(self):
  from quality_spacing import install_spacing_tracking
  class Combined(Model):pass
  install_spacing_tracking(Combined);install_birth_scale_tracking(Combined)
  m=Combined();m.create_from_pcd2_tensor(torch.tensor([[.01,.02,.03]]));m.scales*=10
  m.add_from_pcd2_tensor(torch.tensor([[.1,.2,.3]]));m.prune_points(torch.tensor([False,True]))
  self.assertTrue(torch.equal(m.quality_birth_scales,torch.tensor([[.01,.02,.03]])))
  self.assertTrue(torch.equal(m.quality_initial_spacing,torch.tensor([.02])))

if __name__=='__main__':unittest.main()
