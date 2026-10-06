"""Independent raw RGB-D registration map in estimated coordinates, not truth.

Uses upstream trackable/overlap selections on inserted keyframes. Retains their
raw XYZ and GICP covariance independently of render optimization/opacity/pruning.
No additional observation, reference trajectory, denoising or silent point cap.
"""
import functools,torch

def install_tracking_geometry(model_class,mode,capacity=1000000):
 assert mode in ('render-map','raw-map') and capacity>0
 installed=model_class.__dict__.get('_quality_tracking_geometry')
 if installed is not None:
  assert installed==(mode,capacity),'Cannot switch tracking map mid-run'
  return
 model_class._quality_tracking_geometry=(mode,capacity)
 if mode=='render-map':return
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor
 def capture(self,p,q,s,idx,initial):
  idx=torch.as_tensor(idx,device=p.device,dtype=torch.long)
  assert idx.ndim==1 and len(torch.unique(idx))==len(idx)
  assert not len(idx) or (idx.min()>=0 and idx.max()<len(p))
  xyz=p.detach()[idx].clone();rots=torch.nn.functional.normalize(q.detach()[idx],dim=-1).clone();scales=s.detach()[idx].clone()
  assert xyz.shape==(len(idx),3) and rots.shape==(len(idx),4) and scales.shape==(len(idx),3)
  assert torch.isfinite(xyz).all() and torch.isfinite(rots).all() and torch.isfinite(scales).all() and (scales>0).all()
  assert not len(idx) or (rots.norm(dim=-1)>.99).all()
  previous=0 if initial else len(self.quality_tracking_points)
  if previous+len(idx)>capacity:raise RuntimeError(f'Tracking map capacity {capacity} exceeded: {previous+len(idx)}; no silent drop')
  for name,value in [('points',xyz),('rots',rots),('scales',scales)]:
   key='quality_tracking_'+name
   setattr(self,key,value if initial else torch.cat([getattr(self,key),value]))
 @functools.wraps(create)
 def create_tracked(self,p,c,q,s,z,idx):
  capture(self,p,q,s,idx,True)
  return create(self,p,c,q,s,z,idx)
 @functools.wraps(add)
 def add_tracked(self,p,c,q,s,z,idx):
  capture(self,p,q,s,idx,False)
  return add(self,p,c,q,s,z,idx)
 def target(self,opacity_th):
  # A registration-only map has no optimized opacity. API retained explicitly.
  with torch.no_grad():
   return tuple(getattr(self,'quality_tracking_'+n).cpu().clone() for n in ['points','rots','scales'])
 model_class.create_from_pcd2_tensor=create_tracked
 model_class.add_from_pcd2_tensor=add_tracked
 model_class.get_trackable_gaussians_tensor=target
