"""GS-ICP native CUDA uses XYZW; standard 3DGS viewers read PLY WXYZ.
Only the serialized rotation order changes. Source files remain untouched.
"""
from pathlib import Path
import hashlib,json
import numpy as np
def covariance(q_xyzw,log_scale):
 q=q_xyzw.astype(np.float64);q/=np.linalg.norm(q,axis=1,keepdims=True);x,y,z,w=q.T
 r=np.stack([1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y),2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x),2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)],axis=1).reshape(-1,3,3)
 scaled=r*np.exp(2*log_scale.astype(np.float64))[:,None,:]
 return scaled@r.transpose(0,2,1)
def adapt_xyzw_to_wxyz(source,target):
 source=Path(source);target=Path(target);assert source.resolve()!=target.resolve()
 raw=source.read_bytes();end=raw.index(b'end_header\n')+11;header=raw[:end];lines=header.decode('ascii').splitlines();assert 'format binary_little_endian 1.0' in lines
 properties=[x.split() for x in lines if x.startswith('property ')];assert all(x[1]=='float' for x in properties)
 names=[x[2] for x in properties];count=int(next(x for x in lines if x.startswith('element vertex ')).split()[-1]);a=np.frombuffer(raw[end:],dtype='<f4').reshape(count,len(names));b=a.copy();rot=[names.index('rot_'+str(i)) for i in range(4)];scale=[names.index('scale_'+str(i)) for i in range(3)]
 assert np.isfinite(a).all();b[:,rot]=a[:,[rot[3],rot[0],rot[1],rot[2]]]
 sample=np.linspace(0,count-1,min(count,2048),dtype=int);before=covariance(a[sample][:,rot],a[sample][:,scale]);after=covariance(b[sample][:,[rot[1],rot[2],rot[3],rot[0]]],b[sample][:,scale]);err=float(np.max(np.abs(before-after)));assert err<1e-12
 target.write_bytes(header+b.tobytes());report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),derived_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),vertices=count,source_rotation_order='XYZW',viewer_rotation_order='WXYZ',max_covariance_error=err,covariance_samples=len(sample),unchanged='all fields except rot_0..rot_3 permutation; original source file untouched',evidence='GS-ICP native forward.cu computeCov3D x=q[0],y=q[1],z=q[2],w=q[3]; standard browser buffer expects WXYZ')
 target.with_suffix('.adapter.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
