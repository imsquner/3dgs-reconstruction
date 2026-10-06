import unittest,torch
from test_tracking_covariance import Model
from quality_tracking_geometry import install_tracking_geometry

def make(capacity=1000000):
 cls=type('IndependentGeometry',(Model,),{})
 install_tracking_geometry(cls,'raw-map',capacity)
 m=cls();p=torch.tensor([[0.,0.,1.],[1.,0.,2.]])
 r=torch.tensor([[0.,0.,0.,1.],[0.,0.,0.,1.]])
 s=torch.tensor([[.2,.1,.03],[.6,.4,.03]])
 m.create_from_pcd2_tensor(p,p,r,s,torch.tensor([1.,2.]),[0,1]);return m,p,r,s

class Geometry(unittest.TestCase):
 def test_render_updates_do_not_move_registration_target(self):
  m,p,r,s=make();m.xyz+=5;m.scales*=20;m.rots=torch.roll(m.rots,1,1);m.opacity[:]=0
  a,b,c=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(a,p));self.assertTrue(torch.equal(b,r));self.assertTrue(torch.equal(c,s))
 def test_render_pruning_does_not_remove_tracking_observations(self):
  m,p,_,_=make();m.prune_points(torch.tensor([True,True]))
  self.assertEqual(len(m.xyz),0);self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p))
 def test_add_uses_only_upstream_trackable_indices_without_aliasing(self):
  m,p,r,s=make();new=p+2;m.add_from_pcd2_tensor(new,new,r,s,torch.ones(2),[1]);new+=9
  target=m.get_trackable_gaussians_tensor(.05)[0]
  self.assertEqual(len(target),3);self.assertTrue(torch.equal(target[-1],p[1]+2))
 def test_capacity_exceeded_is_explicit_failure_not_silent_drop(self):
  m,p,r,s=make(2)
  with self.assertRaisesRegex(RuntimeError,'capacity'):
   m.add_from_pcd2_tensor(p,p,r,s,torch.ones(2),[0])
 def test_empty_trackable_add_does_not_create_registration_points(self):
  m,p,r,s=make();m.add_from_pcd2_tensor(p,p,r,s,torch.ones(2),[])
  self.assertEqual(len(m.get_trackable_gaussians_tensor(.05)[0]),2)
 def test_existing_render_priors_still_compose(self):
  from quality_growth import install_birth_scale_tracking
  cls=type('CombinedGeometry',(Model,),{});install_tracking_geometry(cls,'raw-map');install_birth_scale_tracking(cls)
  m=cls();p=torch.zeros(1,3);r=torch.tensor([[0.,0.,0.,1.]]);s=torch.tensor([[.2,.1,.03]])
  m.create_from_pcd2_tensor(p,p,r,s,torch.ones(1),[0]);m.prune_points(torch.tensor([True]))
  self.assertEqual(len(m.quality_birth_scales),0);self.assertEqual(len(m.get_trackable_gaussians_tensor(.05)[0]),1)

if __name__=='__main__':unittest.main()
