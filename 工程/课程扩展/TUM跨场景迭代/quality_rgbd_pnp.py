"""Causal previous RGB-D/current RGB pose measurement. No reference pose inputs."""
import cv2,numpy as np
CONFIG=dict(features=2000,ratio=.75,min_inliers=12,min_fraction=.3,ransac_pixels=3.,iterations=100,confidence=.99,seed=0)
def solve_relative(points,pixels,K):
 points=np.ascontiguousarray(points,dtype=np.float64);pixels=np.ascontiguousarray(pixels,dtype=np.float64);K=np.asarray(K,dtype=np.float64)
 result={'accepted':False,'valid_matches':len(points),'inliers':0}
 if len(points)<CONFIG['min_inliers']:return result
 if not np.isfinite(points).all() or not np.isfinite(pixels).all():return result
 cv2.setRNGSeed(CONFIG['seed'])
 ok,rv,tv,inliers=cv2.solvePnPRansac(points,pixels,K,None,iterationsCount=CONFIG['iterations'],reprojectionError=CONFIG['ransac_pixels'],confidence=CONFIG['confidence'],flags=cv2.SOLVEPNP_EPNP)
 if not ok or inliers is None:return result
 ids=inliers.ravel();result['inliers']=len(ids);result['inlier_fraction']=len(ids)/len(points)
 if len(ids)<CONFIG['min_inliers'] or result['inlier_fraction']<CONFIG['min_fraction']:return result
 ok,rv,tv=cv2.solvePnP(points[ids],pixels[ids],K,None,rv,tv,True,flags=cv2.SOLVEPNP_ITERATIVE)
 if not ok:return result
 T=np.eye(4);T[:3,:3]=cv2.Rodrigues(rv)[0];T[:3,3]=tv.ravel()
 if not np.isfinite(T).all():return result
 residual=np.linalg.norm(cv2.projectPoints(points[ids],rv,tv,K,None)[0].reshape(-1,2)-pixels[ids],axis=1)
 result.update(accepted=True,current_from_previous=T,reprojection_median_pixels=float(np.median(residual)),reprojection_p95_pixels=float(np.percentile(residual,95)))
 return result
def world_from_relative(previous_c2w,current_from_previous):return np.asarray(previous_c2w)@np.linalg.inv(current_from_previous)
def features(image):
 gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
 return cv2.ORB_create(nfeatures=CONFIG['features']).detectAndCompute(gray,None)
def measure(previous_features,current_features,previous_depth_m,K,depth_trunc):
 pk,pd=previous_features;ck,cd=current_features
 if pd is None or cd is None or len(pd)<2 or len(cd)<2:return {'accepted':False,'valid_matches':0,'inliers':0}
 matcher=cv2.BFMatcher(cv2.NORM_HAMMING);forward=matcher.knnMatch(pd,cd,k=2);reverse=matcher.knnMatch(cd,pd,k=2)
 back={m.queryIdx:m.trainIdx for pair in reverse if len(pair)==2 for m,n in [pair] if m.distance<CONFIG['ratio']*n.distance}
 matches=[m for pair in forward if len(pair)==2 for m,n in [pair] if m.distance<CONFIG['ratio']*n.distance and back.get(m.trainIdx)==m.queryIdx]
 xyz=[];uv=[];h,w=previous_depth_m.shape
 for match in matches:
  u,v=pk[match.queryIdx].pt;x,y=int(round(u)),int(round(v))
  if x<0 or x>=w or y<0 or y>=h:continue
  z=float(previous_depth_m[y,x])
  if not np.isfinite(z) or z<.1 or z>depth_trunc:continue
  xyz.append([(u-K[0,2])*z/K[0,0],(v-K[1,2])*z/K[1,1],z]);uv.append(ck[match.trainIdx].pt)
 result=solve_relative(np.array(xyz).reshape(-1,3),np.array(uv).reshape(-1,2),K)
 result['ratio_mutual_matches']=len(matches);return result
