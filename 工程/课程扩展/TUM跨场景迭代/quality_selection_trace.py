"""Read-only tracking membership/prune diagnosis with persistent insertion IDs."""
import functools,json
from pathlib import Path
import numpy as np,torch

def install(model_class,mapper_class,output,limit=80):
 root=Path(output)/'筛选输入'
 create=model_class.create_from_pcd2_tensor;add=model_class.add_from_pcd2_tensor
 prune=model_class.prune_points;target=model_class.get_trackable_gaussians_tensor
 initialize=mapper_class.__init__
 def init(self,system):
  initialize(self,system);self.gaussians.quality_selection_owner=self
 mapper_class.__init__=init
 def frame(model):return int(model.quality_selection_owner.iter_shared[0])
 @functools.wraps(create)
 def created(self,*args,**kwargs):
  result=create(self,*args,**kwargs)
  self.quality_selection_ids=torch.arange(len(self.get_xyz),device=self.get_xyz.device)
  self.quality_selection_next_id=len(self.get_xyz);return result
 @functools.wraps(add)
 def added(self,*args,**kwargs):
  previous=len(self.get_xyz);result=add(self,*args,**kwargs);count=len(self.get_xyz)-previous
  start=self.quality_selection_next_id
  self.quality_selection_ids=torch.cat([self.quality_selection_ids,torch.arange(start,start+count,device=self.get_xyz.device)])
  self.quality_selection_next_id=start+count;return result
 @functools.wraps(prune)
 def pruned(self,mask,*args,**kwargs):
  ids=self.quality_selection_ids
  if frame(self)<limit and bool(mask.any()):
   root.mkdir(exist_ok=True)
   name=f'prune-{frame(self):04d}-{self.quality_selection_owner.train_iter:06d}.npz'
   with torch.no_grad():np.savez(root/name,removed_ids=ids[mask].cpu().numpy(),opacity=self.get_opacity.squeeze(-1)[mask].cpu().numpy(),max_scale=self.get_scaling.max(dim=1).values[mask].cpu().numpy())
   with (root/'prune.jsonl').open('a') as f:f.write(json.dumps(dict(frame=frame(self),iteration=self.quality_selection_owner.train_iter,file=name,count=int(mask.sum())))+'\n')
  kept=ids[~mask].clone();result=prune(self,mask,*args,**kwargs);self.quality_selection_ids=kept
  assert len(kept)==len(self.get_xyz);return result
 def selected(self,threshold):
  result=target(self,threshold)
  if frame(self)<limit:
   root.mkdir(exist_ok=True)
   with torch.no_grad():
    opacity=self.get_opacity.squeeze(-1);mask=self.trackable_mask&(opacity>threshold)
    assert int(mask.sum())==len(result[0])
    np.savez(root/f'selection-{frame(self):04d}.npz',all_ids=self.quality_selection_ids.cpu().numpy(),selected_ids=self.quality_selection_ids[mask].cpu().numpy(),opacity=opacity.cpu().numpy(),trackable=self.trackable_mask.cpu().numpy(),threshold=np.array(threshold),xyz=result[0].numpy())
  return result
 model_class.create_from_pcd2_tensor=created;model_class.add_from_pcd2_tensor=added
 model_class.prune_points=pruned;model_class.get_trackable_gaussians_tensor=selected
