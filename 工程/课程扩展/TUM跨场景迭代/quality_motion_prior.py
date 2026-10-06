"""Causal constant world velocity initial pose, latest two estimates only."""
import numpy as np
from scipy.spatial.transform import Rotation

def predict(estimated_poses,past_timestamps,current_timestamp):
 previous=np.asarray(estimated_poses[-1],dtype=float).copy()
 if len(estimated_poses)<2 or len(past_timestamps)<2:return previous
 older=np.asarray(estimated_poses[-2],dtype=float)
 dt=float(past_timestamps[-1]-past_timestamps[-2]);next_dt=float(current_timestamp-past_timestamps[-1])
 if not np.isfinite(dt+next_dt) or dt<=0 or next_dt<=0 or not np.isfinite(older).all():return previous
 ratio=min(2.,next_dt/dt)
 delta=Rotation.from_matrix(previous[:3,:3]@older[:3,:3].T).as_rotvec()*ratio
 result=previous.copy();result[:3,:3]=Rotation.from_rotvec(delta).as_matrix()@previous[:3,:3]
 result[:3,3]+=ratio*(previous[:3,3]-older[:3,3])
 return result
