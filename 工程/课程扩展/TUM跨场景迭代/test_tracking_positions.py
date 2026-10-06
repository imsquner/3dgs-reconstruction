import unittest,torch
from test_tracking_covariance import Model
from quality_tracking_positions import install_tracking_positions

def make(mode='birth',covariance='optimized'):
 from quality_tracking_covariance import install_tracking_covariance
 cls=type('PositionTrial',(Model,),{});install_tracking_covariance(cls,covariance);install_tracking_positions(cls,mode)
 m=cls();p=torch.tensor([[0.,0.,1.],[1.,0.,2.]])
 r=torch.tensor([[0.,0.,0.,1.],[0.,0.,0.,1.]])
 s=torch.tensor([[.2,.1,.03],[.6,.4,.03]])
 m.create_from_pcd2_tensor(p,p,r,s,torch.tensor([1.,2.]),[0,1]);return m,p,r,s

class Positions(unittest.TestCase):
 def test_birth_positions_remain_fixed_while_covariance_can_optimize(self):
  m,p,r,s=make();m.xyz+=1;m.scales*=2
  xyz,q,cov=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(xyz,p));self.assertTrue(torch.equal(cov,m.scales))
 def test_upstream_opacity_filter_still_rejects_point(self):
  m,p,_,_=make();m.opacity[0]=0
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]))
 def test_upstream_pruning_still_removes_and_aligns_reference(self):
  m,p,_,_=make();m.prune_points(torch.tensor([True,False]))
  self.assertEqual(len(m.quality_tracking_birth_xyz),1)
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p[1:]))
 def test_add_does_not_alias_caller_or_optimized_xyz(self):
  m,p,r,s=make();new=p+2;m.add_from_pcd2_tensor(new,new,r,s,torch.ones(2),[1]);new+=8;m.xyz+=9
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0][-1],p[1]+2))
 def test_raw_covariance_mode_composes_with_birth_positions(self):
  m,p,r,s=make(covariance='raw-gicp');m.xyz+=1;m.scales*=5;m.prune_points(torch.tensor([False,True]))
  xyz,q,cov=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(xyz,p[:1]));self.assertTrue(torch.equal(cov,s[:1]))
 def test_optimized_positions_are_original_behavior(self):
  m,p,_,_=make('optimized');m.xyz+=3
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[0],p+3))

if __name__=='__main__':unittest.main()
