"""Only previous observation cache and previous estimated world pose."""
import numpy as np
from quality_rgbd_pnp import features,measure,world_from_relative
class RgbdInitial:
 def __init__(self,K,depth_scale,depth_trunc):
  self.K=np.array(K);self.depth_scale=depth_scale;self.depth_trunc=depth_trunc;self.frame=-1;self.previous_features=None;self.previous_depth=None
 def update(self,frame,current_bgr,current_depth_raw,previous_estimated_c2w):
  assert frame==self.frame+1,'Observation order changed'
  current_features=features(current_bgr);previous=np.array(previous_estimated_c2w,dtype=float,copy=True)
  result={'accepted':False,'reason':'first-observation'}
  if self.frame>=0:result=measure(self.previous_features,current_features,self.previous_depth,self.K,self.depth_trunc)
  initial=world_from_relative(previous,result['current_from_previous']) if result['accepted'] else previous
  self.previous_features=current_features;self.previous_depth=np.array(current_depth_raw,dtype=float,copy=True)/self.depth_scale;self.frame=frame
  return initial,result
