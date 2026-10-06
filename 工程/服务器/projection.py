import torch,numpy as np,json
from pathlib import Path

def patch_camera():
 from scene.shared_objs import SharedCam
 original=SharedCam.__init__
 def init(self,*args,**kwargs):
  original(self,*args,**kwargs)
  W=float(self.image_width[0]);H=float(self.image_height[0]);P=self.projection_matrix
  P[0,0]=2*float(self.fx[0])/W;P[1,1]=2*float(self.fy[0])/H
  P[2,0]=(2*float(self.cx[0])+1)/W-1;P[2,1]=(2*float(self.cy[0])+1)/H-1
  self.update_matrix()
 SharedCam.__init__=init

def check():
 W,H,fx,fy,cx,cy=640,480,535.4,539.2,320.1,247.6
 P=np.zeros((4,4));P[0,0]=2*fx/W;P[1,1]=2*fy/H;P[0,2]=(2*cx+1)/W-1;P[1,2]=(2*cy+1)/H-1;P[3,2]=1
 pts=np.array([[0,0,1,1],[.1,.2,1.4,1],[-.4,-.3,2,1]])
 clip=pts@P.T;ndc=clip[:,:2]/clip[:,3,None];pix=((ndc+1)*[W,H]-1)/2
 ref=pts[:,:2]/pts[:,2,None]*[fx,fy]+[cx,cy]
 residual=float(np.max(np.abs(pix-ref)));assert residual<1e-10
 return dict(max_residual_pixels=residual,centered_projection_offset_pixels=[(W-1)/2-cx,(H-1)/2-cy],formula='ndc2Pix(v,S)=((v+1)*S-1)/2, matching rasterizer aux.h',scope='Numerical projection consistency only; not a new physical camera calibration')
if __name__=='__main__':print(json.dumps(check(),indent=2))
