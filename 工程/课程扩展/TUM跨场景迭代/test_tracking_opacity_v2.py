import unittest,torch
from test_tracking_covariance import Model
from quality_tracking_covariance import install_tracking_covariance
from quality_tracking_positions import install_tracking_positions
from quality_tracking_opacity_v2 import install_tracking_opacity

def make(mode,positions='birth'):
 cls=type('OpacityTrial',(Model,),{})
 install_tracking_covariance(cls,'raw-gicp');install_tracking_positions(cls,positions);install_tracking_opacity(cls,mode)
 m=cls();p=torch.tensor([[0.,0.,1.],[1.,0.,2.]]);q=torch.tensor([[0.,0.,0.,1.]]*2);s=torch.tensor([[.2,.1,.03],[.6,.4,.03]])
 m.create_from_pcd2_tensor(p,p,q,s,torch.ones(2),[0,1]);return m,p,q,s

class Opacity(unittest.TestCase):
 def test_learned_mode_keeps_original_rejection(self):
  m,p,_,_=make('learned');m.opacity[0]=0
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]))
 def test_birth_mode_ignores_render_opacity_and_xyz_updates(self):
  m,p,q,s=make('birth');m.opacity.zero_();m.xyz+=9;m.scales*=3
  xyz,rot,cov=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(xyz,p));self.assertTrue(torch.equal(rot,q));self.assertTrue(torch.equal(cov,s))
 def test_birth_mode_retains_trackable_filter(self):
  m,p,_,_=make('birth');m.trackable_mask[0]=False
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]))
 def test_pruning_remains_active_and_aligned(self):
  m,p,_,_=make('birth');m.opacity.zero_();m.prune_points(torch.tensor([True,False]))
  self.assertEqual(len(m.quality_tracking_birth_opacity),1)
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]))
 def test_new_references_do_not_take_old_learned_opacity(self):
  m,p,q,s=make('birth');m.opacity.zero_();m.add_from_pcd2_tensor(p+3,p,q,s,torch.ones(2),[0,1]);m.opacity.zero_()
  self.assertEqual(len(m.get_trackable_gaussians_tensor(.05)[0]),4)
  self.assertTrue((m.quality_tracking_birth_opacity>.05).all())

class OptimizedXYZ(unittest.TestCase):
 def test_uses_current_xyz_but_born_opacity_and_raw_covariance(self):
  m,p,q,s=make('birth','optimized');m.opacity.zero_();m.xyz+=9;m.scales*=3
  xyz,rot,cov=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(xyz,p+9));self.assertTrue(torch.equal(rot,q));self.assertTrue(torch.equal(cov,s))
 def test_retains_trackable_and_prune_alignment(self):
  m,p,q,s=make('birth','optimized');m.xyz+=9;m.opacity.zero_();m.prune_points(torch.tensor([True,False]))
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]+9))
  m.trackable_mask[:]=False;self.assertEqual(len(m.get_trackable_gaussians_tensor(.05)[0]),0)
if __name__=='__main__':unittest.main()
