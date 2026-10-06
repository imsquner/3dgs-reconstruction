"""Trajectory and scheduled-input tracking telemetry; no model evaluation fitting."""
import json,argparse
from pathlib import Path
import numpy as np
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();R=E/'运行'/a.run
manifest=json.loads((R/'manifest.json').read_text());rows=manifest['frames'];est=np.array(json.loads((R/'final-poses.json').read_text()));ref=np.array([x['reference_c2w'] for x in rows]);assert est.shape==ref.shape
x=est[:,:3,3];y=ref[:,:3,3];xc=x-x.mean(0);yc=y-y.mean(0);u,_,vt=np.linalg.svd(yc.T@xc);d=np.eye(3);d[2,2]=np.linalg.det(u@vt);rot=u@d@vt;aligned=xc@rot.T+y.mean(0);ate=np.linalg.norm(aligned-y,axis=1)
rpe=[];rrot=[]
for i in range(1,len(est)):
 er=np.linalg.inv(np.linalg.inv(ref[i-1])@ref[i])@(np.linalg.inv(est[i-1])@est[i]);rpe.append(np.linalg.norm(er[:3,3]));rrot.append(np.rad2deg(np.arccos(np.clip((np.trace(er[:3,:3])-1)/2,-1,1))))
timing=[json.loads(x) for x in (R/'tracking-timing.jsonl').read_text().splitlines()];assert len(timing)==len(rows)
lat=[x['tracking_latency_seconds'] for x in timing if x['tracking_latency_seconds'] is not None]
summary=json.loads((R/'summary.json').read_text());mapping=json.loads((R/'mapping-summary.json').read_text())
variant=manifest['quality_args'].get('variant','original')
record={'run':a.run,'trajectory':{'ate_rigid_aligned_rmse_m':float(np.sqrt(np.mean(ate**2))),'rpe_adjacent_retained_translation_rmse_m':float(np.sqrt(np.mean(np.array(rpe)**2))),'rpe_adjacent_retained_rotation_rmse_degrees':float(np.sqrt(np.mean(np.array(rrot)**2))),'scope':'SE3 rigid alignment for ATE metric only, no scale; RPE adjacent retained observations, not fixed temporal interval; no alignment applied to image/depth evaluation'},'timing':{'scheduled_input_fps':manifest['quality_args'].get('input_fps',0),'frames':len(timing),'dropped_frames':0,'tracking_latency_p50_p95_max_seconds':np.quantile(lat,[.5,.95,1]).tolist() if lat else None,'tracking_completion_span_seconds':timing[-1]['completion_monotonic']-timing[0]['completion_monotonic'],'wall_including_workers_and_mapper_completion_seconds':summary['wall_seconds'],'scope':'Tracking completion latency includes decode/GICP/keyframe mapper waits. File replay retains late frames. Does not measure every-frame end-to-end map readiness; mapper tail and initialization included only in total wall.'},'mapping':mapping,'signature':{'poses':sha256(R/'final-poses.json'),'timing':sha256(R/'tracking-timing.jsonl'),'manifest':sha256(R/'manifest.json')}}
record['variant']=variant
if (R/'mapping-timing.jsonl').exists():
 events=[json.loads(line) for line in (R/'mapping-timing.jsonl').read_text().splitlines()]
 budget=manifest['quality_args']['steps_per_frame']
 assert [e['mapping_iteration'] for e in events]==list(range(budget,mapping['mapping_iterations']+1,budget)),'Mapping event sequence incomplete'
 assert all(events[i]['completion_monotonic']>=events[i-1]['completion_monotonic'] for i in range(1,len(events)))
 record['map_updates']={'events':len(events),'first_monotonic':events[0]['completion_monotonic'],'last_monotonic':events[-1]['completion_monotonic'],
  'map_update_tail_after_tracking_completion_seconds':max(0.,events[-1]['completion_monotonic']-timing[-1]['completion_monotonic']),
  'gradient_bearing_optimizer_step_calls':mapping.get('gradient_bearing_optimizer_step_calls'),
  'scope':'Map optimizer update events at fixed budget boundaries, with latest tracking frame and latest inserted keyframe in JSONL. Not proof every input frame contributes a keyframe or a completed map. Tail excludes final file saving and worker shutdown.'}
 record['signature']['mapping_timing']=sha256(R/'mapping-timing.jsonl')
if (R/'评价/metrics.json').exists():
 metric=json.loads((R/'评价/metrics.json').read_text());assert metric['signature']['map']==sha256(R/'scene.ply')
 record['validation']=metric['means'];record['validation_frames']=metric['validation_frames']
if (R/'评价/common-depth.json').exists():record['common_depth']=json.loads((R/'评价/common-depth.json').read_text())['means']
atomic_json(R/'online-audit.json',record)
(R/'实验记录.md').write_text('\n'.join(['# '+a.run,'','GS-ICP在线实验，variant='+variant+'；帧数='+str(len(rows))+'，校准投影、留出RGB/深度组、固定总映射预算。','原地图未覆盖；本记录不自动宣称质量验收通过。离线精修另计，不计入在线速度。','轨迹：'+json.dumps(record['trajectory'],ensure_ascii=False),'输入与跟踪：'+json.dumps(record['timing'],ensure_ascii=False),'地图：'+json.dumps({k:v for k,v in mapping.items() if k!='keyframe_indices'},ensure_ascii=False),'地图更新事件：'+json.dumps(record.get('map_updates','旧版本未记录'),ensure_ascii=False),'留出指标：'+json.dumps(record.get('validation','尚未评价'),ensure_ascii=False),'共同深度：'+json.dumps(record.get('common_depth','尚未评价'),ensure_ascii=False),'实际stage日志在课程扩展/TUM跨场景迭代/日志；运行manifest记录源码和输入。评价独立保存于评价/metrics.json。','显存为mapper进程PyTorch allocated峰值，非整机/含全部native库峰值。spawn显式种子不等于整个异步建图位精确确定。']),encoding='utf-8')
print('ONLINE_AUDIT',record['trajectory'],record['timing'],flush=True)
