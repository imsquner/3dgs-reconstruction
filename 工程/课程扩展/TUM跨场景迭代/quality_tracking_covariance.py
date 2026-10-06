"""Covariance-only tracking ablation; means, opacity and pruning remain coupled."""
import functools,torch

def install_tracking_covariance(model_class,mode):
 assert mode in ('optimized','birth-render','raw-gicp')
 installed=model_class.__dict__.get('_quality_tracking_covariance_mode')
 if installed is not None:
  assert installed==mode,'A model class cannot switch covariance mode mid-run'
  return
 model_class._quality_tracking_covariance_mode=mode
 if mode=='optimized':return
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor;prune=model_class.prune_points
 def reference(model,rots,scales,start):
  selected=scales if mode=='raw-gicp' else model.get_scaling[start:]
  s=selected.detach().clone();q=torch.nn.functional.normalize(rots.detach(),dim=-1).clone()
  assert s.shape==(len(rots),3) and q.shape==(len(rots),4)
  assert torch.isfinite(s).all() and (s>0).all() and torch.isfinite(q).all() and (q.norm(dim=-1)>.99).all()
  return q,s
 @functools.wraps(create)
 def create_tracked(self,points,colors,rots_,scales_,z_vals_,trackable_idxs):
  result=create(self,points,colors,rots_,scales_,z_vals_,trackable_idxs)
  self.quality_tracking_rots,self.quality_tracking_scales=reference(self,rots_,scales_,0)
  return result
 @functools.wraps(add)
 def add_tracked(self,points,colors,rots_,scales_,z_vals_,trackable_idxs):
  old_q=self.quality_tracking_rots;old_s=self.quality_tracking_scales;assert len(old_s)==len(self.get_scaling)
  result=add(self,points,colors,rots_,scales_,z_vals_,trackable_idxs);q,s=reference(self,rots_,scales_,len(old_s))
  self.quality_tracking_rots=torch.cat([old_q,q]);self.quality_tracking_scales=torch.cat([old_s,s]);assert len(self.quality_tracking_scales)==len(self.get_scaling)
  return result
 @functools.wraps(prune)
 def prune_tracked(self,mask,*args,**kwargs):
  old_q=self.quality_tracking_rots;old_s=self.quality_tracking_scales;assert mask.dtype==torch.bool and len(mask)==len(old_s)
  result=prune(self,mask,*args,**kwargs);self.quality_tracking_rots=old_q[~mask];self.quality_tracking_scales=old_s[~mask]
  assert len(self.quality_tracking_scales)==len(self.get_scaling);return result
 def target(self,opacity_th):
  with torch.no_grad():
   mask=(self.get_opacity.squeeze(-1)>opacity_th)&self.trackable_mask
   assert len(mask)==len(self.quality_tracking_scales)
   return self.get_xyz[mask].cpu(),self.quality_tracking_rots[mask].cpu(),self.quality_tracking_scales[mask].cpu()
 model_class.create_from_pcd2_tensor=create_tracked;model_class.add_from_pcd2_tensor=add_tracked;model_class.prune_points=prune_tracked
 model_class.get_trackable_gaussians_tensor=target
