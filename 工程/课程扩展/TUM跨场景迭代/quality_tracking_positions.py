"""Position-only target ablation; original opacity/trackable/pruning retained."""
import functools,torch

def install_tracking_positions(model_class,mode):
 assert mode in ('optimized','birth')
 installed=model_class.__dict__.get('_quality_tracking_positions')
 if installed is not None:
  assert installed==mode,'Cannot switch tracking position source mid-run'
  return
 model_class._quality_tracking_positions=mode
 if mode=='optimized':return
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor
 prune=model_class.prune_points;target=model_class.get_trackable_gaussians_tensor
 @functools.wraps(create)
 def create_tracked(self,p,c,q,s,z,idx):
  xyz=p.detach().clone();assert torch.isfinite(xyz).all()
  result=create(self,p,c,q,s,z,idx);self.quality_tracking_birth_xyz=xyz
  return result
 @functools.wraps(add)
 def add_tracked(self,p,c,q,s,z,idx):
  xyz=p.detach().clone();assert torch.isfinite(xyz).all()
  result=add(self,p,c,q,s,z,idx)
  self.quality_tracking_birth_xyz=torch.cat([self.quality_tracking_birth_xyz,xyz])
  return result
 @functools.wraps(prune)
 def prune_tracked(self,mask):
  keep=self.quality_tracking_birth_xyz[~mask].clone()
  result=prune(self,mask);self.quality_tracking_birth_xyz=keep
  assert len(keep)==len(self.get_xyz)
  return result
 def target_tracked(self,threshold):
  _,rots,scales=target(self,threshold)
  with torch.no_grad():
   mask=self.trackable_mask&(self.get_opacity.squeeze(-1)>threshold)
   xyz=self.quality_tracking_birth_xyz[mask].cpu().clone()
   assert len(xyz)==len(rots)==len(scales)
   return xyz,rots,scales
 model_class.create_from_pcd2_tensor=create_tracked
 model_class.add_from_pcd2_tensor=add_tracked
 model_class.prune_points=prune_tracked
 model_class.get_trackable_gaussians_tensor=target_tracked
