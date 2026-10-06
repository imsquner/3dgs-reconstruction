"""Birth-scale references aligned with online Gaussian insertion and pruning."""
import functools
import torch

def middle_spacing(scales):
 value=scales.detach().sort(dim=-1,descending=True).values[:,1].clone()
 assert torch.isfinite(value).all() and (value>0).all(),'Invalid birth spacing'
 return value

def install_spacing_tracking(model_class):
 if model_class.__dict__.get('_quality_spacing_installed',False):return
 create=model_class.create_from_pcd2_tensor
 add=model_class.add_from_pcd2_tensor
 prune=model_class.prune_points
 @functools.wraps(create)
 def create_tracked(self,*args,**kwargs):
  result=create(self,*args,**kwargs)
  self.quality_initial_spacing=middle_spacing(self.get_scaling)
  return result
 @functools.wraps(add)
 def add_tracked(self,*args,**kwargs):
  old=self.quality_initial_spacing
  assert len(old)==len(self.get_scaling),'Spacing lost alignment before insertion'
  result=add(self,*args,**kwargs)
  self.quality_initial_spacing=torch.cat([old,middle_spacing(self.get_scaling[len(old):])])
  assert len(self.quality_initial_spacing)==len(self.get_scaling)
  return result
 @functools.wraps(prune)
 def prune_tracked(self,mask,*args,**kwargs):
  old=self.quality_initial_spacing
  assert mask.dtype==torch.bool and len(mask)==len(old),'Prune mask lost alignment'
  result=prune(self,mask,*args,**kwargs)
  self.quality_initial_spacing=old[~mask]
  assert len(self.quality_initial_spacing)==len(self.get_scaling)
  return result
 model_class.create_from_pcd2_tensor=create_tracked
 model_class.add_from_pcd2_tensor=add_tracked
 model_class.prune_points=prune_tracked
 model_class._quality_spacing_installed=True
