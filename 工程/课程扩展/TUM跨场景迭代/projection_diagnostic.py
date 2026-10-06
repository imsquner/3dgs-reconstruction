"""Geometric footprint descriptor only: visibility/occlusion is not resolved."""
import numpy as np
from scipy.spatial.transform import Rotation
def project_covariance(xyz,scales,quaternions,c2w,intrinsic):
    _,_,fx,fy,cx,cy=intrinsic
    R=Rotation.from_quat(quaternions).as_matrix()
    C=(R*scales[:,None,:]**2)@R.transpose(0,2,1)
    Rc=c2w[:3,:3];p=(xyz-c2w[:3,3])@Rc
    C=Rc.T[None]@C@Rc[None]
    z=p[:,2];safe=np.where(abs(z)>1e-6,z,1e-6)
    xy=np.stack([fx*p[:,0]/safe+cx,fy*p[:,1]/safe+cy],-1)
    J=np.zeros((len(p),2,3));J[:,0,0]=fx/safe;J[:,1,1]=fy/safe;J[:,0,2]=-fx*p[:,0]/safe**2;J[:,1,2]=-fy*p[:,1]/safe**2
    cov=J@C@J.transpose(0,2,1)+np.eye(2)[None]*.3
    return xy,cov,z

def footprint_mask(xy,cov,z,opacity,width,height):
    mask=np.zeros((height,width),bool);visible=0
    for center,C,depth,alpha in zip(xy,cov,z,opacity):
        if depth<=.2 or alpha<=.5 or not np.isfinite(C).all():continue
        qmax=2*np.log(alpha/.05);radius=np.sqrt(qmax*np.diag(C))
        lo=np.floor(center-radius).astype(int);hi=np.ceil(center+radius).astype(int)
        x0,y0=max(0,lo[0]),max(0,lo[1]);x1,y1=min(width,hi[0]+1),min(height,hi[1]+1)
        if x0>=x1 or y0>=y1:continue
        yy,xx=np.mgrid[y0:y1,x0:x1];delta=np.stack([xx-center[0],yy-center[1]],-1)
        q=np.einsum('...i,ij,...j->...',delta,np.linalg.inv(C),delta);part=q<=qmax
        if part.any():visible+=1;mask[y0:y1,x0:x1]|=part
    return mask,visible
