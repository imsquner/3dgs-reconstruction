import unittest,torch
from quality_tracking_covariance import install_tracking_covariance

class Model:
 @property
 def get_xyz(self):return self.xyz
 @property
 def get_scaling(self):return self.scales
 @property
 def get_rotation(self):return torch.nn.functional.normalize(self.rots,dim=-1)
 @property
 def get_opacity(self):return self.opacity
 def create_from_pcd2_tensor(self,p,c,r,s,z,idx):
  self.xyz=p.clone();self.rots=r.clone();self.scales=s/torch.clamp_min(2*z**1.5,1)[:,None];self.opacity=torch.full((len(p),1),.1);self.trackable_mask=torch.zeros(len(p),dtype=torch.bool);self.trackable_mask[idx]=True
 def add_from_pcd2_tensor(self,p,c,r,s,z,idx):
  self.xyz=torch.cat([self.xyz,p]);self.rots=torch.cat([self.rots,r]);self.scales=torch.cat([self.scales,s/torch.clamp_min(2*z**1.5,1)[:,None]])
  self.opacity=torch.cat([self.opacity,torch.full((len(p),1),.1)]);mask=torch.zeros(len(p),dtype=torch.bool);mask[idx]=True;self.trackable_mask=torch.cat([self.trackable_mask,mask])
 def prune_points(self,mask):
  for name in ['xyz','rots','scales','opacity','trackable_mask']:setattr(self,name,getattr(self,name)[~mask])
 def get_trackable_gaussians_tensor(self,threshold):
  mask=self.trackable_mask&(self.opacity[:,0]>threshold)
  return self.xyz[mask],self.get_rotation[mask],self.scales[mask]

def model(mode):
 cls=type('Trial',(Model,),{});install_tracking_covariance(cls,mode);m=cls()
 p=torch.tensor([[0.,0.,1.],[1.,0.,2.]]);r=torch.tensor([[0.,0.,0.,1.],[0.,0.,0.,1.]]);s=torch.tensor([[.2,.15,.03],[.6,.4,.03]])
 m.create_from_pcd2_tensor(p,p,r,s,torch.tensor([1.,2.]),[0,1]);return m,s,r

class Covariance(unittest.TestCase):
 def test_raw_references_cannot_be_changed_by_render_optimization(self):
  m,s,r=model('raw-gicp');m.scales*=20;m.rots=torch.roll(m.rots,1,1)
  _,actual_r,actual_s=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(actual_s,s));self.assertTrue(torch.equal(actual_r,r))
 def test_birth_render_preserves_depth_scaled_initial_value(self):
  m,s,r=model('birth-render');initial=m.scales.clone();m.scales*=20
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[2],initial));self.assertFalse(torch.equal(initial,s))
 def test_optimized_mode_is_upstream_behavior(self):
  m,_,_=model('optimized');m.scales*=20
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[2],m.scales))
 def test_add_prune_and_opacity_filter_remain_aligned(self):
  m,s,r=model('raw-gicp');m.prune_points(torch.tensor([True,False]));p=torch.tensor([[2.,0.,2.]])
  extra=torch.tensor([[.7,.5,.1]]);m.add_from_pcd2_tensor(p,p,r[:1],extra,torch.tensor([2.]),[0])
  m.opacity[0]=0.;out=m.get_trackable_gaussians_tensor(.05)
  self.assertTrue(torch.equal(out[0],p));self.assertTrue(torch.equal(out[2],extra))
 def test_existing_growth_trackers_compose(self):
  from quality_growth import install_birth_scale_tracking
  from quality_spacing import install_spacing_tracking
  cls=type('Combined',(Model,),{});install_spacing_tracking(cls);install_birth_scale_tracking(cls);install_tracking_covariance(cls,'raw-gicp')
  m=cls();p=torch.zeros(1,3);r=torch.tensor([[0.,0.,0.,1.]]);s=torch.tensor([[.2,.1,.03]]);m.create_from_pcd2_tensor(p,p,r,s,torch.ones(1),[0]);m.scales*=10
  self.assertTrue(torch.equal(m.get_trackable_gaussians_tensor(.05)[2],s));self.assertTrue(torch.equal(m.quality_birth_scales,s/2))

if __name__=='__main__':unittest.main()
