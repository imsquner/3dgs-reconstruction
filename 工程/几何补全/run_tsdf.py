"""Frozen-input RGB-D TSDF with independent diagnostic reference-pose arm."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import cv2
import numpy as np
import open3d as o3d
from geometry_contract import validate_pose, validate_split, depth_reliability


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''): h.update(block)
    return h.hexdigest()


def atomic(p, v):
    p = Path(p); t = p.with_suffix('.tmp')
    t.write_text(json.dumps(v, indent=2), encoding='utf-8'); t.replace(p)


def resolve(path, root):
    name = 'rgbd_dataset_freiburg3_long_office_household/'
    if name not in path: raise ValueError('Unexpected source dataset')
    return root / path.split(name, 1)[1]


def previous_consistency(z, pose, previous, K):
    """Reject contradicted depths; unseen/occluded locations remain unknown and retained."""
    if not previous: return np.ones(z.shape, bool)
    h, w = z.shape; _, _, fx, fy, cx, cy = K
    yy, xx = np.indices(z.shape)
    local = np.stack(((xx-cx)*z/fx, (yy-cy)*z/fy, z), axis=-1).reshape(-1, 3)
    world = local @ pose[:3, :3].T + pose[:3, 3]
    supported = np.zeros(len(world), bool); checked = np.zeros(len(world), bool)
    for old_z, old_pose in previous:
        inv = validate_pose(old_pose); p = world @ inv[:3, :3].T + inv[:3, 3]
        front = p[:, 2] > 0.1
        denom = np.maximum(p[:, 2], 0.001)
        u = np.rint(p[:, 0]/denom*fx+cx).astype(int)
        v = np.rint(p[:, 1]/denom*fy+cy).astype(int)
        inside = front & (u >= 0) & (u < w) & (v >= 0) & (v < h)
        ix = np.where(inside)[0]; sampled = old_z[v[ix], u[ix]]
        observed = sampled > 0.1
        # If old depth is nearer, this point was occluded rather than contradicted.
        comparable = observed & (sampled >= p[ix, 2]-0.04)
        checked[ix[comparable]] = True
        supported[ix[observed & (np.abs(sampled-p[ix, 2]) <= 0.04)]] = True
    return (~checked | supported).reshape(z.shape)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--frames', type=int, required=True)
    ap.add_argument('--pose', choices=['estimated', 'reference'], default='estimated')
    ap.add_argument('--variant', choices=['raw','range','edge','bilateral','consistent','combined'], default='raw')
    a = ap.parse_args(); b = Path(a.root); inputs = b/'input'
    proto = json.loads((inputs/'protocol.json').read_text())
    m = json.loads((inputs/'manifest.json').read_text())
    all_rows = m['frames']; rows = all_rows[:a.frames]
    estimates = np.array(json.loads((inputs/'final-poses.json').read_text()))
    assert len(estimates) == len(all_rows) and len(rows) == a.frames
    assert [r['source_frame'] for r in all_rows] == [r['source_frame'] for r in proto['upstream_original_train']]
    validate_split(all_rows, proto['upstream_original_validation'])
    dataset = inputs/'rgbd_dataset_freiburg3_long_office_household'
    w, h, fx, fy, cx, cy = K = proto['intrinsic']
    trunc = proto.get('depth_trunc', 3.0)
    out = b/'runs'/('%s-%s-%d' % (a.pose, a.variant, a.frames)); out.mkdir(parents=True, exist_ok=True)
    cfg = dict(frames=a.frames, pose=a.pose, variant=a.variant, voxel_m=0.01, sdf_trunc_m=0.04,
        depth_trunc_m=trunc, range_candidate_trunc_m=2.5, depth_scale=proto['depth_scale'],
        repeat_policy='retain frozen frame association and repeated depth contributions in all arms',
        reference_scope='diagnostic only', open3d=o3d.__version__, code_sha256=sha(__file__),
        contract_sha256=sha(Path(__file__).with_name('geometry_contract.py')),
        source_hashes={name:sha(inputs/name) for name in ['manifest.json','protocol.json','final-poses.json','scene.ply']},
        stage_resume='completed meshes reused only with matching signature; partial TSDF restarts integration',
        mask_limits='heuristic candidates, no blanket thin-structure deletion')
    signature = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    if (out/'result.json').exists():
        old=json.loads((out/'result.json').read_text())
        if old['signature']==signature and sha(out/'mesh-raw.ply')==old['mesh_sha256']:
            print('REUSE_COMPLETE',out.name,flush=True); return
        raise ValueError('Existing completed output has another signature')
    atomic(out/'manifest.json',cfg)
    volume=o3d.pipelines.integration.ScalableTSDFVolume(voxel_length=.01,sdf_trunc=.04,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    intrinsic=o3d.camera.PinholeCameraIntrinsic(w,h,fx,fy,cx,cy)
    start=time.monotonic(); last=start; kept=total=0; previous=[]; input_h=hashlib.sha256()
    for i,row in enumerate(rows):
        rgbp=resolve(row['rgb_path'],dataset); dp=resolve(row['depth_path'],dataset)
        rgb=cv2.cvtColor(cv2.imread(str(rgbp)),cv2.COLOR_BGR2RGB)
        raw=cv2.imread(str(dp),-1)
        assert rgb.shape==(h,w,3) and raw.shape==(h,w)
        input_h.update(bytes.fromhex(sha(rgbp))); input_h.update(bytes.fromhex(sha(dp)))
        pose=np.array(row['reference_c2w']) if a.pose=='reference' else estimates[i]
        inv=validate_pose(pose)
        z=raw.astype(np.float32)/proto['depth_scale']
        valid=depth_reliability(z,'raw',trunc); total+=int(valid.sum())
        if a.variant=='range': valid &= z < 2.5
        if a.variant in ('edge','combined'): valid &= depth_reliability(z,'edge',trunc)
        if a.variant=='bilateral':
            filtered=cv2.bilateralFilter(z,5,.02,2)
            # Invalid depth is not filled; large changes are rejected, not substituted.
            small=np.abs(filtered-z)<=.02
            z=np.where(valid & small,filtered,z)
        if a.variant in ('consistent','combined'):
            valid &= previous_consistency(z,pose,previous,K)
        z=np.where(valid,z,0).astype(np.float32); kept+=int(valid.sum())
        rgbd=o3d.geometry.RGBDImage.create_from_color_and_depth(o3d.geometry.Image(np.ascontiguousarray(rgb)),
            o3d.geometry.Image(z),depth_scale=1.,depth_trunc=trunc,convert_rgb_to_intensity=False)
        volume.integrate(rgbd,intrinsic,inv)
        previous.append((raw.astype(np.float32)/proto['depth_scale'],pose)); previous=previous[-3:]
        now=time.monotonic()
        if i==0 or i==len(rows)-1 or now-last>=10:
            elapsed=now-start
            state=dict(stage='integrating',pid=os.getpid(),frames=i+1,total=len(rows),seconds=elapsed,
                       eta_seconds=elapsed/(i+1)*(len(rows)-i-1),timestamp=time.time(),signature=signature)
            atomic(out/'checkpoint.json',state);print('HEARTBEAT',out.name,json.dumps(state),flush=True);last=now
    mesh=volume.extract_triangle_mesh(); mesh.compute_vertex_normals()
    assert len(mesh.vertices)>0 and len(mesh.triangles)>0
    assert np.isfinite(np.asarray(mesh.vertices)).all()
    o3d.io.write_triangle_mesh(str(out/'mesh-raw.ply'),mesh,write_ascii=False)
    labels,counts,areas=mesh.cluster_connected_triangles()
    counts=np.asarray(counts); areas=np.asarray(areas)
    result=dict(signature=signature,frames=len(rows),vertices=len(mesh.vertices),triangles=len(mesh.triangles),
        components=len(counts),small_components_lt100_faces=int((counts<100).sum()),
        small_component_faces=int(counts[counts<100].sum()),small_component_area_m2=float(areas[counts<100].sum()),
        raw_mesh_area_m2=float(mesh.get_surface_area()),depth_pixels_retained_fraction=kept/max(1,total),
        input_observation_sha256=input_h.hexdigest(),mesh_sha256=sha(out/'mesh-raw.ply'),
        seconds=time.monotonic()-start,completed=True,quality_passed=None,
        note='Small components are detection only; no cleaned geometry replaces raw output.')
    atomic(out/'result.json',result);atomic(out/'checkpoint.json',dict(stage='complete',signature=signature,timestamp=time.time()))
    print('TSDF_COMPLETE',out.name,json.dumps(result),flush=True)


if __name__=='__main__': main()
