import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'源码/GS-ICP-SLAM'))
import cv2,numpy as np,pygicp
from types import SimpleNamespace
from utils.traj_utils import TrajManager
from mp_Tracker import Tracker
data='/root/.local/share/monogs/gpt-6/data/tum-office';traj=TrajManager('tum',data)
d=SimpleNamespace(W=640,H=480,fx=535.4,fy=539.2,cx=320.1,cy=247.6,depth_scale=5000.,depth_trunc=3.)
d.downsample_idxs,d.x_pre,d.y_pre=Tracker.set_downsample_filter(d,10)
def points(i):
 rgb=cv2.imread(traj.color_paths[i]);depth=cv2.imread(traj.depth_paths[i],cv2.IMREAD_ANYDEPTH)
 return Tracker.downsample_and_make_pointcloud2(d,depth,rgb)
reg=pygicp.FastGICP();reg.set_num_threads(2);reg.set_max_correspondence_distance(.02);reg.set_max_knn_distance(99999.)
p,c,z,valid=points(0);T=traj.gt_poses[0];p=(T[:3,:3]@p.T).T+T[:3,3];f=np.zeros(len(p),dtype=np.int32);f[valid]=np.arange(1,len(valid)+1,dtype=np.int32)
print('TARGET',p.shape,len(valid),flush=True);reg.set_input_target(p);reg.set_target_filter(len(valid),f);reg.calculate_target_covariance_with_filter();print('TARGET_COV_DONE',flush=True)
p,c,z,valid=points(1);f=np.zeros(len(p),dtype=np.int32);f[valid]=np.arange(1,len(valid)+1,dtype=np.int32);reg.set_input_source(p);reg.set_source_filter(len(valid),f);print('ALIGN_START',p.shape,len(valid),flush=True)
result=reg.align(T);print('ALIGN_DONE',result,flush=True);assert np.isfinite(result).all()
