import csv,json,hashlib
from pathlib import Path
import numpy as np,yaml
B=Path(__file__).resolve().parents[1]/'数据'/'EndoSLAM';T=B/'tum-mono-subset240';T.mkdir(exist_ok=True)
rows=list(csv.DictReader((B/'colon_position_rotation.csv').open()))[:240]
rgb=['# timestamp path'];depth=['# timestamp path'];poses=['# timestamp tx ty tz qx qy qz qw']
for i,row in enumerate(rows):
 t=float(row['time(s)']);image=f'image_{i:04d}.png';d=f'aov_image_{i:04d}.png'
 assert (B/'subset240'/'rgb'/image).exists() and (B/'subset240'/'depth'/d).exists()
 rgb.append(f'{t:.9f} ../subset240/rgb/{image}');depth.append(f'{t:.9f} ../subset240/depth/{d}')
 # Unity left-handed x-right/y-up/z-forward -> OpenCV x-right/y-down/z-forward.
 values=[float(row[k]) for k in ['tX','tY','tZ','rX','rY','rZ','rW']]
 values[1]*=-1;values[3]*=-1;values[5]*=-1
 poses.append(f'{t:.9f} '+' '.join(f'{v:.9f}' for v in values))
for name,lines in [('rgb.txt',rgb),('depth.txt',depth),('groundtruth.txt',poses)]: (T/name).write_text('\n'.join(lines)+'\n')
K=np.loadtxt(B/'cam.txt',delimiter=',').reshape(3,3)
config={'inherit_from':'/mnt/d/桌面/image/gpt-6/工程/源码/MonoGS-speedup/configs/mono/tum/base_config.yaml','Dataset':{'dataset_path':str(T),'Calibration':dict(fx=float(K[0,0]),fy=float(K[1,1]),cx=float(K[0,2]),cy=float(K[1,2]),k1=0.,k2=0.,p1=0.,p2=0.,k3=0.,distorted=False,width=320,height=320,depth_scale=1.)}}
(T/'mono.yaml').write_text(yaml.safe_dump(config))
audit=dict(scene='EndoSLAM UnityCam synthetic colon',frames=240,input_fps=30,camera_source='UnityCam/Calibration/cam.txt',coordinate_conversion='Assumed Unity left-handed to OpenCV through y reflection in both camera/world bases',coordinate_conversion_verified_against_render=False,depth_used=False,depth_encoding_unresolved=True,trajectory_unit='Unity world unit; not confirmed metric',pose_use='initialization/reference only; tracker estimates subsequent poses',status='development_adapter_only')
(T/'adapter-manifest.json').write_text(json.dumps(audit,indent=2));print('MEDICAL_MONOCULAR_ADAPTER_READY',audit,flush=True)
