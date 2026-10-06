import json,re,hashlib
from pathlib import Path
import cv2,numpy as np
from plyfile import PlyData
from evo.core.trajectory import PosePath3D,align_trajectory
B=Path(__file__).resolve().parents[1]/'运行';reports=[]
for run in sorted(B.glob('gsicp-*')):
 if not run.is_dir():continue
 logfile=B/(run.name+'.log');log=logfile.read_text(errors='replace') if logfile.exists() else '';exitfile=B/(run.name+'.exit')
 report=dict(run=run.name,launcher_exit=int(exitfile.read_text()) if exitfile.exists() else None,traceback='Traceback' in log)
 if not (run/'summary.json').exists():report['status']='failed_or_incomplete';reports.append(report);continue
 summary=json.loads((run/'summary.json').read_text());report.update(summary);manifest=json.loads((run/'manifest.json').read_text());report['manifest']=manifest
 snapshot=B/'源码快照'/(run.name+'.py');report['source_snapshot_verified']=hashlib.sha256(snapshot.read_bytes()).hexdigest()==manifest['wrapper_sha256']
 rows=[json.loads(x) for x in (run/'frames.jsonl').read_text().splitlines()];report['frame_records']=len(rows);report['contiguous_frames']=[r['frame'] for r in rows]==list(range(summary['frames']))
 fps=re.findall(r'System FPS: ([0-9.]+)',log);report['official_tracking_fps']=float(fps[-1]) if fps else None
 report['post_first_tracking_fps']=(len(rows)-1)/(rows[-1]['wall_seconds']-rows[0]['wall_seconds']);report['processing_ms_p50_p95']=np.percentile([r['processing_seconds']*1000 for r in rows],[50,95]).tolist()
 ages=[r['arrival_to_tracking_complete_seconds'] for r in rows];report['arrival_to_tracking_ms_p50_p95']=np.percentile(np.array(ages)*1000,[50,95]).tolist();report['final_backlog_seconds']=ages[-1];report['latency_pass_200ms']=bool(np.percentile(ages,95)<=.2)
 gt=np.array([r['reference_c2w'] for r in rows]);est=np.array([r['estimated_c2w'] for r in rows]);ref=PosePath3D(poses_se3=gt);aligned=align_trajectory(PosePath3D(poses_se3=est),ref,correct_scale=False);report['all_frame_ate_rmse_m']=float(np.sqrt(np.mean(np.sum((aligned.positions_xyz-ref.positions_xyz)**2,axis=1))));report['alignment']='SE(3)';report['metric_unit']='meter'
 timestamps=np.array([float(Path(r['image_path']).stem) for r in rows]);rpe=[]
 for i,t in enumerate(timestamps):
  j=int(np.argmin(np.abs(timestamps-t-1)))
  if j<=i or abs(timestamps[j]-t-1)>.05:continue
  dr=np.linalg.inv(gt[i])@gt[j];de=np.linalg.inv(aligned.poses_se3[i])@aligned.poses_se3[j];rpe.append(np.linalg.norm((np.linalg.inv(dr)@de)[:3,3]))
 report['rpe_1second_pairs']=len(rpe);report['rpe_1second_rmse_m']=float(np.sqrt(np.mean(np.square(rpe)))) if rpe else None
 ply=PlyData.read(str(run/'scene.ply'))['vertex'].data;report['ply_count']=len(ply);report['nonfinite_fields']={n:int((~np.isfinite(ply[n])).sum()) for n in ply.dtype.names if not np.isfinite(ply[n]).all()};report['ply_finite']=not report['nonfinite_fields']
 report['mapping']=json.loads((run/'mapping-summary.json').read_text());maps=[json.loads(x) for x in (run/'map-frames.jsonl').read_text().splitlines()];report['observed_map_frames']=len(maps);report['map_render_update_interval_seconds_max']=float(np.max(np.diff([r['monotonic'] for r in maps]))) if len(maps)>1 else None
 if manifest['input_fps'] and maps:report['map_render_ready_age_ms_p50_p95']=np.percentile([r['map_render_ready_age_seconds']*1000 for r in maps],[50,95]).tolist()
 updates=run/'mapping-updates.jsonl'
 if updates.exists():
  steps=[json.loads(x) for x in updates.read_text().splitlines()];interval=np.diff([x['monotonic'] for x in steps]);report['observed_optimizer_step_batches']=len(steps);report['ten_step_mapping_interval_p50_p95_max_seconds']=np.percentile(interval,[50,95,100]).tolist() if len(interval) else None
 if (run/'online-map.mp4').exists():
  cap=cv2.VideoCapture(str(run/'online-map.mp4'));count=0;fps=cap.get(cv2.CAP_PROP_FPS)
  while cap.read()[0]:count+=1
  cap.release();report['video']=dict(decoded_frames=count,encoder_fps=fps,duration_seconds=count/fps,matches_summary=count==report['mapping']['recorded_frames'],scope=report['mapping']['recording_scope'])
 report['status']='valid_artifacts' if report['launcher_exit']==0 and summary['worker_exitcodes']==[0,0] and not report['traceback'] and report['source_snapshot_verified'] and report['contiguous_frames'] and report['ply_finite'] else 'partial_or_invalid'
 (run/'experiment-audit.json').write_text(json.dumps(report,indent=2));reports.append(report);print(json.dumps({k:v for k,v in report.items() if k not in ('manifest',)}),flush=True)
(B/'GSICP实验汇总.json').write_text(json.dumps(reports,indent=2))
