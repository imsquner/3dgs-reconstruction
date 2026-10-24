"""CPU raycast evaluation on frozen holdout observations and inherited nine view definitions."""
import argparse
import json
import os
from pathlib import Path
import time
import cv2
import numpy as np
import open3d as o3d
from run_tsdf import atomic, sha, resolve


def raycast(scene, mesh, pose, K, scale=2):
    w,h,fx,fy,cx,cy=K;h//=scale;w//=scale
    yy,xx=np.indices((h,w));xx=xx*scale;yy=yy*scale
    direction=np.stack(((xx-cx)/fx,(yy-cy)/fy,np.ones((h,w))),axis=-1)
    world=direction@pose[:3,:3].T
    rays=np.concatenate((np.broadcast_to(pose[:3,3],world.shape),world),axis=-1).astype(np.float32)
    result=scene.cast_rays(o3d.core.Tensor(rays))
    depth=result['t_hit'].numpy();hit=np.isfinite(depth)&(depth>0)
    colors=np.zeros((h,w,3),np.float32)
    if hit.any():
        indices=result['primitive_ids'].numpy()[hit].astype(np.int64)
        faces=np.asarray(mesh.triangles)[indices]
        uv=result['primitive_uvs'].numpy()[hit]
        weights=np.column_stack((1-uv.sum(1),uv))
        vertex_colors=np.asarray(mesh.vertex_colors)
        if len(vertex_colors):colors[hit]=(vertex_colors[faces]*weights[:,:,None]).sum(1)
        else: colors[hit]=.7
    return depth,colors,hit


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--run',required=True)
    a=ap.parse_args();b=Path(a.root);out=b/'runs'/a.run;inp=b/'input'
    cfg=json.loads((out/'manifest.json').read_text());n=cfg['frames']
    proto=json.loads((inp/'protocol.json').read_text());m=json.loads((inp/'manifest.json').read_text())
    poses=np.array(json.loads((inp/'final-poses.json').read_text()))[:n]
    hold=[r for r in proto['upstream_original_validation'] if r['source_frame']<=m['frames'][n-1]['source_frame']]
    mesh=o3d.io.read_triangle_mesh(str(out/'mesh-raw.ply'));scene=o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    ev=out/'evaluation';ev.mkdir(exist_ok=True);(ev/'predictions').mkdir(exist_ok=True)
    signature=dict(mesh=sha(out/'mesh-raw.ply'),protocol=sha(inp/'protocol.json'),evaluator=sha(__file__),
        evaluation_scale=2,ray_depth='camera-z, unnormalized optical rays',
        split='frozen original validation; all within training-prefix source-frame range',
        inherited_fixed_views='indices 0,n//2,n-1; local-x offsets 0,.2,.4',
        coverage='valid reference depth intersect finite positive mesh depth; no Gaussian alpha criterion',
        note='Mesh protocol is explicit; not byte-identical historical Gaussian renderer evaluation')
    if (ev/'metrics.json').exists():
        old=json.loads((ev/'metrics.json').read_text())
        if old['signature']==signature:print('EVALUATION_REUSED',a.run,flush=True);return
        raise ValueError('Changed evaluator cannot overwrite previous evidence')
    atomic(ev/'evaluation-protocol.json',signature)
    rows=[];start=time.monotonic();last=start
    for j,r in enumerate(hold):
        p=np.array(r['reference_c2w']);pred,color,hit=raycast(scene,mesh,p,proto['intrinsic'])
        ref=cv2.imread(str(resolve(r['depth_path'],inp/'rgbd_dataset_freiburg3_long_office_household')),-1)[::2,::2].astype(float)/proto['depth_scale']
        valid=np.isfinite(ref)&(ref>.1)&(ref<proto.get('depth_trunc',3.));covered=valid&hit
        err=pred[covered]-ref[covered]
        rows.append(dict(source_frame=r['source_frame'],valid_pixels=int(valid.sum()),covered_pixels=int(covered.sum()),
            coverage=float(covered.sum()/max(1,valid.sum())),depth_mae_m=float(abs(err).mean()) if len(err) else None,
            depth_rmse_m=float(np.sqrt(np.mean(err**2))) if len(err) else None))
        np.savez_compressed(ev/'predictions'/('%05d.npz'%r['source_frame']),depth=pred,covered=covered,reference=ref,valid=valid)
        now=time.monotonic()
        if j==0 or j==len(hold)-1 or now-last>10:
            print('EVAL_HEARTBEAT',a.run,j+1,len(hold),'eta',round((now-start)/(j+1)*(len(hold)-j-1),1),flush=True);last=now
    views=[]
    for i in sorted({0,n//2,n-1}):
        for offset in (0.,.2,.4):
            p=poses[i].copy();p[:3,3]+=p[:3,0]*offset
            depth,color,hit=raycast(scene,mesh,p,proto['intrinsic'])
            filename='free-%04d-%.1f.png'%(i,offset)
            cv2.imwrite(str(ev/filename),cv2.cvtColor((np.clip(color,0,1)*255).astype('uint8'),cv2.COLOR_RGB2BGR))
            # Normals/depth remain separate from raw vertex-color visualization.
            np.savez_compressed(ev/filename.replace('.png','.npz'),depth=depth,hit=hit,c2w=p)
            views.append(dict(train_index=i,offset_local_x_m=offset,image=filename))
    means={k:float(np.mean([r[k] for r in rows if r[k] is not None])) for k in ['coverage','depth_mae_m','depth_rmse_m']}
    atomic(ev/'metrics.json',dict(signature=signature,rows=rows,means=means,validation_frames=len(hold),
        fixed_views=views,seconds=time.monotonic()-start,visual_review_passed=None))
    print('EVALUATION_COMPLETE',a.run,json.dumps(means),flush=True)


if __name__=='__main__':main()
