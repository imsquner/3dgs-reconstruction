"""Opacity-source ablation only; upstream trackable mask and pruning retained."""
import functools,torch

def install_tracking_opacity(model_class,mode):
 assert mode in ('learned','birth')
 installed=model_class.__dict__.get('_quality_tracking_opacity_mode')
 if installed is not None:
  assert installed==mode,'Cannot change opacity source during a run'
  return
 model_class._quality_tracking_opacity_mode=mode
 if mode=='learned':return
 assert model_class._quality_tracking_positions in ('birth','optimized') and model_class._quality_tracking_covariance_mode=='raw-gicp','Birth opacity trial requires declared raw geometry references'
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor;prune=model_class.prune_points
 def snapshot(model,start=0):
  values=model.get_opacity.squeeze(-1)[start:].detach().clone()
  assert torch.isfinite(values).all() and ((values>=0)&(values<=1)).all()
  return values
 @functools.wraps(create)
 def created(self,*args,**kwargs):
  result=create(self,*args,**kwargs);self.quality_tracking_birth_opacity=snapshot(self);return result
 @functools.wraps(add)
 def added(self,*args,**kwargs):
  old=self.quality_tracking_birth_opacity;result=add(self,*args,**kwargs)
  self.quality_tracking_birth_opacity=torch.cat([old,snapshot(self,len(old))]);return result
 @functools.wraps(prune)
 def pruned(self,mask,*args,**kwargs):
  keep=self.quality_tracking_birth_opacity[~mask].clone();result=prune(self,mask,*args,**kwargs)
  self.quality_tracking_birth_opacity=keep;assert len(keep)==len(self.get_xyz);return result
 def selected(self,threshold):
  with torch.no_grad():
   mask=self.trackable_mask&(self.quality_tracking_birth_opacity>threshold)
   xyz=self.quality_tracking_birth_xyz if self._quality_tracking_positions=='birth' else self.get_xyz
   assert len(mask)==len(xyz)==len(self.quality_tracking_scales)
   return xyz[mask].detach().cpu(),self.quality_tracking_rots[mask].cpu(),self.quality_tracking_scales[mask].cpu()
 model_class.create_from_pcd2_tensor=created;model_class.add_from_pcd2_tensor=added
 model_class.prune_points=pruned;model_class.get_trackable_gaussians_tensor=selected
