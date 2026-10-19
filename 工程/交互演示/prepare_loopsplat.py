"""Export separate LoopSplat submaps and matching processed RGB-D replay. No optimization."""
import pathlib,sys,os,json,hashlib,numpy as np,torch
from PIL import Image
from argparse import ArgumentParser
BASE=pathlib.Path(__file__).resolve().parent;TASK=BASE.parent/'LoopSplat复现';REPO=TASK/'源码';os.chdir(REPO);sys.path.insert(0,str(REPO))
from src.entities.gaussian_model import GaussianModel
from src.entities.arguments import OptimizationParams
from src.entities.datasets import get_dataset
from src.utils.io_utils import load_config

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def export():
    audit=json.loads((TASK/'验收/association-audit.json').read_text());results=[]
    for run in ('smoke30-a2','stress150-a2'):
        source=TASK/'结果'/run;cfg=load_config(str(source/'config.yaml'));ds=get_dataset(cfg['dataset_name'])({**cfg['data'],**cfg['cam']});poses=torch.load(source/'estimated_c2w.ckpt',map_location='cpu').numpy();verification=json.loads((source/'verification.json').read_text())
        for m,checkpoint in enumerate(sorted((source/'submaps').glob('*.ckpt'))):
            print('EXPORT_START',run,m,flush=True);digest=sha(checkpoint);obj=torch.load(checkpoint,map_location='cuda');ids=obj['submap_keyframes'];assert ids==list(range(ids[0],ids[-1]+1));count=obj['gaussian_params']['xyz'].shape[0]
            out=BASE/'assets/natural/loopsplat'/run/f'sm{m}';(out/'input').mkdir(parents=True,exist_ok=True);prefix='assets/natural/loopsplat/'+run+f'/sm{m}/'
            model=GaussianModel(sh_degree=0);model.restore_from_params(obj['gaussian_params'],OptimizationParams(ArgumentParser()));model.save_ply(str(out/'map.ply'));xyz=model.get_xyz().detach().cpu().numpy();assert np.isfinite(xyz).all()
            # LoopSplat and browser PLY both use WXYZ, exp(log-scale) and sigmoid(opacity).
            rotation=obj['gaussian_params']['rotation'].cpu().numpy();assert np.isfinite(rotation).all() and np.all(np.linalg.norm(rotation,axis=1)>0)
            subposes=poses[ids];times=np.array([audit['rows'][i]['rgb']['timestamp'] for i in ids]);times-=times[0]
            chunks=[];seen=set();allpoints=[];allcolors=[];first=[];total=0;images=[];input_hashes=[]
            yy,xx=np.mgrid[0:ds.height:6,0:ds.width:6]
            for local,i in enumerate(ids):
                _,rgb,depth,_=ds[i];assert rgb.shape==(ds.height,ds.width,3)
                image=out/'input'/f'{i:05d}.png';Image.fromarray(rgb).save(image);images.append(prefix+'input/'+image.name)
                z=depth[::6,::6];valid=np.isfinite(z)&(z>.1)&(z<5)
                camera=np.stack([(xx-ds.cx)*z/ds.fx,(yy-ds.cy)*z/ds.fy,z],axis=-1)[valid];world=(camera@poses[i,:3,:3].T+poses[i,:3,3]).astype('<f4');colors=rgb[::6,::6][valid]
                keep=[]
                for j,key in enumerate(map(tuple,np.floor(world/.015).astype('int32'))):
                    if key not in seen:seen.add(key);keep.append(j)
                allpoints.append(world[keep]);allcolors.append(colors[keep]);first.extend([local]*len(keep));prior=total;total+=len(keep)
                chunks.append(dict(source_frame=i,time_seconds=float(times[local]),point_count=total,added=total-prior,input_image=images[-1]))
                row=audit['rows'][i];assert sha(pathlib.Path(ds.color_paths[i]))==row['rgb']['sha256'] and sha(pathlib.Path(ds.depth_paths[i]))==row['depth']['sha256'];input_hashes.append({'frame':i,'rgb_sha256':row['rgb']['sha256'],'depth_sha256':row['depth']['sha256'],'processed_rgb_sha256':sha(image)})
            points=np.concatenate(allpoints);colors=np.concatenate(allcolors);assert len(points)==total and np.isfinite(points).all();(out/'observations.xyz').write_bytes(points.tobytes());(out/'observations.rgb').write_bytes(colors.astype('u1').tobytes());(out/'point-first-frame.u32').write_bytes(np.array(first,dtype='<u4').tobytes())
            scope='本子地图范围的RGB-D观测回放：原深度与记录的估计位姿，每帧、每6像素采样，0.1–5m深度，1.5cm体素保留首次观测；不是历史Gaussian状态，未验证有效闭环。'
            accum=dict(points=total,source_frames=len(ids),sampled_frames=len(ids),frame_stride=1,pixel_stride=6,voxel_m=.015,depth_range_m=[.1,5],chunks=chunks,frame_times=times.tolist(),caption='本子图逐帧RGB-D观测',scope=scope)
            write(out/'accumulation.json',accum)
            lo,hi=np.quantile(xyz,[.01,.99],axis=0);extent=max(float(np.linalg.norm(hi-lo)),.5);views=[]
            for k in np.linspace(0,len(ids)-1,3,dtype=int):
                p=subposes[k];position=p[:3,3];forward=p[:3,2];up=-p[:3,1];right=p[:3,0]
                for off in (0,-.03,.03):
                    vpos=position+right*off;views.append(dict(name=f'源帧{ids[k]}'+(f' 横移{off:.2f}m' if off else ''),position=vpos.tolist(),look_at=(vpos+forward).tolist(),up=up.tolist(),kind='training-path' if off==0 else 'offset-diagnostic'))
            if len(ids)==1:
                p=subposes[0];position=p[:3,3];forward=p[:3,2];up=-p[:3,1];right=p[:3,0];views=[]
                for dx in (-.03,0,.03):
                    for dy in (-.03,0,.03):
                        vpos=position+right*dx+up*dy;views.append(dict(name=f'单帧视角 横移{dx:.2f}m / 升降{dy:.2f}m',position=vpos.tolist(),look_at=(vpos+forward).tolist(),up=up.tolist(),kind='training-path' if dx==0 and dy==0 else 'offset-diagnostic'))
            arm='smoke30' if run.startswith('smoke30') else 'stress150';sceneid=f'loopsplat-{arm}-sm{m}';experiment='30帧原参数' if arm=='smoke30' else '150帧低预算'
            info=f'{experiment} · 子地图{m} · {len(ids)}帧（源帧{ids[0]}–{ids[-1]}）\n全段初始化＋SLAM {verification["slam_s"]:.1f}秒 · 子图独立查看\n短链路通过；无有效闭环；质量未验收'+('\n末子图仅1帧，孔洞/破碎明显。' if len(ids)==1 else '')
            scene=dict(id=sceneid,label=f'LoopSplat · {experiment} / 子地图{m}',kind='RGB-D SLAM短测 · 独立子地图',run=run,ply=prefix+'map.ply',gaussians=int(count),indices=ids,poses=subposes.tolist(),frame_times=times.tolist(),input_fps=30,duration=float(times[-1]),intrinsic=[ds.width,ds.height,ds.fx,ds.fy,ds.cx,ds.cy],map_bounds=[lo.tolist(),hi.tolist()],movement_extent=extent,point_size=.012,marker_size=.012,near=.005,far=max(50,extent*10),fixed_views=views,spherical_harmonics_degree=0,gaussian_quaternion_order='wxyz',splat_alpha_threshold=0,offline=False,show_rgb_preview=True,rgb_images=images,time_precision=3,display_info=info,tracking_text='本机短测（非实时）',tracking_label='实验状态',ate_m=None,ate_label='子图ATE',ate_text='未单独评价',accumulation_path=prefix+'accumulation.json',points_path=prefix+'observations.xyz',colors_path=prefix+'observations.rgb',accumulation_description=scope,bounds='固定的最终独立Gaussian子地图＋估计相机轨迹回放；非历史建图状态。无有效闭环，注册/PGO未验证。'+('此子图仅1帧，孔洞/破碎明显。' if len(ids)==1 else ''),coordinate_id=run+'-world',scale_units='metres from RGB-D',source_checkpoint=str(checkpoint),source_checkpoint_sha256=digest)
            write(out/'scene.json',scene);assert sha(checkpoint)==digest
            proof=dict(passed=True,id=sceneid,source_checkpoint_sha256=digest,gaussians=int(count),keyframes=ids,pose_convention='OpenCV camera-to-world; X right,Y down,Z forward',quaternion='WXYZ unchanged',rgb_preprocessing='Official dataset loader undistort then crop; 380x540 matching shifted intrinsics',input_hashes=input_hashes,observation_points=total,independent_submap=True,not_merged=True,files={f:sha(out/f) for f in ('map.ply','scene.json','accumulation.json','observations.xyz','observations.rgb','point-first-frame.u32')})
            write(out/'asset-verification.json',proof);results.append(proof);del model,obj;torch.cuda.empty_cache();print('EXPORT_DONE',sceneid,count,total,flush=True)
    dest=TASK/'验收/网页接入';dest.mkdir(exist_ok=True);write(dest/'asset-audit.json',dict(passed=True,scenes=results));print('ALL_READY',len(results),flush=True)
if __name__=='__main__':export()
