"""Publish offline COLMAP observations without changing experiment originals.

Positions use the final globally optimized model: this is an offline observation
replay, not causal online triangulation or historical Gaussian optimizer states.
"""
from pathlib import Path
import hashlib, json, shutil, struct, time
import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent / 'OOOSplat办公室实验'
JOB = ROOT / '任务/full-office-shared-sfm-r1'
OUT = BASE / 'assets/natural/ooosplat-office/balanced'
PREFIX = 'assets/natural/ooosplat-office/balanced/'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()

def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

def rotation(q):
    w,x,y,z=q
    return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
                     [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
                     [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    model = JOB/'shared-model'
    cameras = {}
    parameter_counts = {0:3,1:4,2:4,3:5,4:8,5:8,6:12,7:5,8:4,9:5,10:12,11:16}
    model_names = {0:'SIMPLE_PINHOLE',1:'PINHOLE',2:'SIMPLE_RADIAL',3:'RADIAL',4:'OPENCV',5:'OPENCV_FISHEYE',6:'FULL_OPENCV',7:'FOV',8:'SIMPLE_RADIAL_FISHEYE',9:'RADIAL_FISHEYE',10:'THIN_PRISM_FISHEYE',11:'RAD_TAN_THIN_PRISM_FISHEYE'}
    with (model/'cameras.bin').open('rb') as f:
        for _ in range(struct.unpack('<Q', f.read(8))[0]):
            cid,mid,w,h=struct.unpack('<iiQQ', f.read(24))
            p=struct.unpack('<'+'d'*parameter_counts[mid], f.read(8*parameter_counts[mid]))
            fx,fy,cx,cy=(p[0],p[0],p[1],p[2]) if mid in (0,2,3,8,9) else p[:4]
            cameras[cid]=dict(width=w,height=h,fx=fx,fy=fy,cx=cx,cy=cy,model=model_names[mid],params=p)
    rows=[]; observations={}
    with (model/'images.bin').open('rb') as f:
        for _ in range(struct.unpack('<Q',f.read(8))[0]):
            vals=struct.unpack('<idddddddi',f.read(64)); name=bytearray()
            while True:
                b=f.read(1)
                if not b: raise ValueError('Truncated image filename')
                if b==b'\0': break
                name.extend(b)
            name=name.decode('utf-8'); n=struct.unpack('<Q',f.read(8))[0]
            point_ids=np.empty(n,dtype=np.int64)
            for j in range(n): point_ids[j]=struct.unpack('<ddq',f.read(24))[2]
            observations[vals[0]]=point_ids
            q=np.array(vals[1:5]); t=np.array(vals[5:8]); r=rotation(q)
            assert abs(np.linalg.norm(q)-1)<1e-6 and np.allclose(r@r.T,np.eye(3),atol=1e-6)
            c2w=np.eye(4); c2w[:3,:3]=r.T; c2w[:3,3]=-r.T@t
            assert np.allclose(r@c2w[:3,3]+t,0,atol=1e-8)
            rows.append(dict(image_id=vals[0],name=name,timestamp=float(Path(name).stem),pose=c2w.tolist(),intrinsic=cameras[vals[8]]))
    rows.sort(key=lambda x:x['timestamp']); assert len(rows)==2585
    times=np.array([r['timestamp'] for r in rows]); assert np.all(np.diff(times)>0)
    frame_by_id={r['image_id']:i for i,r in enumerate(rows)}
    xyz=[]; rgb=[]; first=[]; point_ids=[]; track_entries=0
    with (model/'points3D.bin').open('rb') as f:
        count=struct.unpack('<Q',f.read(8))[0]
        for _ in range(count):
            vals=struct.unpack('<QdddBBBdQ',f.read(51)); frames=[]
            assert vals[8]>0 and np.isfinite(vals[1:4]).all()
            for j in range(vals[8]):
                iid,idx=struct.unpack('<ii',f.read(8))
                assert iid in frame_by_id and 0<=idx<len(observations[iid])
                assert observations[iid][idx]==vals[0], 'Non-reciprocal COLMAP track'
                frames.append(frame_by_id[iid]); track_entries+=1
            xyz.append(vals[1:4]); rgb.append(vals[4:7]); first.append(min(frames)); point_ids.append(vals[0])
        assert not f.read(1)
    assert count==120823 and len(set(point_ids))==count
    order=np.lexsort((np.array(point_ids), np.array(first)))
    xyz=np.array(xyz,dtype='<f4')[order]; rgb=np.array(rgb,dtype='u1')[order]; first=np.array(first)[order]
    (OUT/'observations.xyz').write_bytes(xyz.tobytes()); (OUT/'observations.rgb').write_bytes(rgb.tobytes())
    (OUT/'point-first-frame.u32').write_bytes(first.astype('<u4').tobytes())
    source=ROOT/'输入/office-all-rgb'; (OUT/'input').mkdir(exist_ok=True)
    chunks=[]; hashes={}; t0=times[0]
    for i,row in enumerate(rows):
        src=source/row['name']; dst=OUT/'input'/row['name']
        source_hash=sha(src)
        if not dst.exists() or sha(dst)!=source_hash: shutil.copy2(src,dst)
        assert sha(dst)==source_hash
        hashes[row['name']]=source_hash
        upto=int(np.searchsorted(first,i,side='right')); prior=chunks[-1]['point_count'] if chunks else 0
        chunks.append(dict(source_frame=i,time_seconds=float(times[i]-t0),timestamp=float(times[i]),point_count=upto,added=upto-prior,input_image=PREFIX+'input/'+row['name'],rgb_path=row['name'],rgb_sha256=source_hash))
        if i%200==0: print('ASSET_HEARTBEAT',i,len(rows),flush=True)
    ply=JOB/'results/balanced/final.ply'; shutil.copy2(ply,OUT/'final.ply'); assert sha(ply)==sha(OUT/'final.ply')
    with ply.open('rb') as f:
        header=b''
        while b'end_header\n' not in header: header+=f.readline()
    assert b'element vertex 500544' in header and b'f_rest_44' in header
    centers=np.array([r['pose'] for r in rows])[:,:3,3]; bounds=[centers.min(0).tolist(),centers.max(0).tolist()]; extent=float(np.linalg.norm(np.ptp(centers,axis=0)))
    intr=rows[0]['intrinsic']; views=json.loads((ROOT/'验收/full-office-shared-sfm-r1/views.json').read_text(encoding='utf-8')); assert len(views)==15
    scope='COLMAP 离线稀疏观测回放：最终优化坐标按 track 首次观测出现；不是因果在线建图、RGB-D稠密累计或历史Gaussian状态。SfM尺度未标定。'
    accumulation=dict(points=count,source_frames=len(rows),sampled_frames=len(rows),frame_stride=1,point_sampling='none',chunks=chunks,frame_times=[c['time_seconds'] for c in chunks],caption='每帧RGB · 离线稀疏观测回放',scope=scope,points_path=PREFIX+'observations.xyz',colors_path=PREFIX+'observations.rgb',first_frame_path=PREFIX+'point-first-frame.u32',position_sha256=sha(OUT/'observations.xyz'),color_sha256=sha(OUT/'observations.rgb'))
    write('accumulation.json',accumulation)
    scene=dict(id='ooosplat-office-balanced',label='OOOSplat办公室 · 均衡15000步',kind='RGB离线重建 · 最终3DGS',run=JOB.name,ply=PREFIX+'final.ply',ply_sha256=sha(ply),gaussians=500544,indices=list(range(1,len(rows)+1)),poses=[r['pose'] for r in rows],frame_times=(times-t0).tolist(),image_names=[r['name'] for r in rows],image_ids=[r['image_id'] for r in rows],camera_intrinsics=[r['intrinsic'] for r in rows],intrinsic=[intr[k] for k in ('width','height','fx','fy','cx','cy')],duration=float(times[-1]-t0),map_bounds=bounds,movement_extent=extent,point_size=extent*.0015,marker_size=extent*.008,near=max(extent*.0005,.00001),far=extent*25,offline=True,spherical_harmonics_degree=3,gaussian_quaternion_order='wxyz',accumulation_path=PREFIX+'accumulation.json',points_path=PREFIX+'observations.xyz',colors_path=PREFIX+'observations.rgb',fixed_views=views,coordinate_id='ooosplat-office-shared-sfm-r1',accumulation_description=scope,bounds='最终Gaussian固定地图＋COLMAP估计相机轨迹回放；非实时建图、非历史Gaussian状态。RGB离线重建，SfM尺度未标定。',splat_alpha_threshold=0,observation_video=PREFIX+'observation-accumulation.mp4',ate_m=None,training_steps=15000,input_count=len(rows),sparse_points=count,scale_units='unscaled SfM units')
    write('scene.json',scene)
    provenance=dict(source_model=str(model),source_ply=str(ply),model_hashes={n:sha(model/n) for n in ('images.bin','cameras.bin','points3D.bin')},ply_sha256=sha(ply),input_hashes=hashes,semantics=scope,training_steps=15000,depth_used=False,ground_truth_used=False,pose_convention='COLMAP OpenCV camera-to-world; local +X right, +Y down, +Z forward',gaussian_quaternion_order='wxyz',distortion_boundary='输入面板保留未经畸变校正的原始RGB；浏览器相机使用pinhole投影，不应用COLMAP径向畸变参数，边缘可能存在对齐差异。完整畸变参数已保存在camera_intrinsics。',created_unix=time.time())
    write('provenance.json',provenance)
    assert chunks[-1]['point_count']==count and all(c['added']>=0 for c in chunks)
    write('asset-verification.json',dict(passed=True,cameras=len(rows),points=count,track_entries_checked=track_entries,reciprocal_tracks_verified=True,all_rgb_sha256_verified=True,all_pose_roundtrips_verified=True,duration=scene['duration'],gaussians=500544,ply_sha256=sha(ply),fixed_views=len(views),monotonic_point_count=True,files={n:sha(OUT/n) for n in ('scene.json','accumulation.json','observations.xyz','observations.rgb','point-first-frame.u32','provenance.json','final.ply')},runtime_visual_verified=False))
    print('ASSETS_READY',json.dumps(dict(cameras=len(rows),points=count,duration=scene['duration'],extent=extent,track_entries=track_entries)),flush=True)

if __name__=='__main__': main()
