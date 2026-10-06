"""Soft tangential-scale growth prior relative to measured Gaussian birth scales."""
import functools,torch

def growth_regularizer(scales,birth_scales,factor=8.):
 assert scales.shape==birth_scales.shape and factor>1
 current=scales.sort(dim=-1,descending=True).values[:,:2]
 reference=birth_scales.detach().sort(dim=-1,descending=True).values[:,:2]
 excess=torch.relu(torch.log(current/reference.clamp_min(1e-6)/factor))
 terms=excess.square().sum(dim=-1)
 return terms.sum()/(terms.detach()>0).sum().clamp_min(1)

def birth_scales(scales):
 value=scales.detach().clone()
 assert torch.isfinite(value).all() and (value>0).all()
 return value

def install_birth_scale_tracking(model_class):
 if model_class.__dict__.get('_quality_birth_scales_installed',False):return
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor;prune=model_class.prune_points
 @functools.wraps(create)
 def create_tracked(self,*args,**kwargs):
  result=create(self,*args,**kwargs);self.quality_birth_scales=birth_scales(self.get_scaling);return result
 @functools.wraps(add)
 def add_tracked(self,*args,**kwargs):
  old=self.quality_birth_scales;assert len(old)==len(self.get_scaling)
  result=add(self,*args,**kwargs)
  self.quality_birth_scales=torch.cat([old,birth_scales(self.get_scaling[len(old):])]);assert self.quality_birth_scales.shape==self.get_scaling.shape
  return result
 @functools.wraps(prune)
 def prune_tracked(self,mask,*args,**kwargs):
  old=self.quality_birth_scales;assert mask.dtype==torch.bool and len(mask)==len(old)
  result=prune(self,mask,*args,**kwargs);self.quality_birth_scales=old[~mask];assert self.quality_birth_scales.shape==self.get_scaling.shape
  return result
 model_class.create_from_pcd2_tensor=create_tracked;model_class.add_from_pcd2_tensor=add_tracked;model_class.prune_points=prune_tracked
 model_class._quality_birth_scales_installed=True
