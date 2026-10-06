import json,hashlib,re
from pathlib import Path
import numpy as np,yaml
from evo.core.trajectory import PosePath3D,align_trajectory
from plyfile import PlyData
B=Path(__file__).resolve().parents[1]/'运行';reports=[]
for run in sorted(B.iterdir()):
 if not run.is_dir() or not (run/'manifest.json').exists():continue
 if not run.name.startswith(('speedup-','medical-')):continue
 report=dict(run=run.name)
 exitfile=B/(run.name+'.exit');report['launcher_exit']=int(exitfile.read_text()) if exitfile.exists() else None
 logfile=B/(run.name+'.log');log=logfile.read_text(errors='replace') if logfile.exists() else ''
 report['traceback']='Traceback (most recent call last)' in log
 report['backend_returned']='BACKEND_LOOP_RETURNED' in log
 report['complete_marker']='COMPLETE ' in log
 report['cuda_ipc_warning']='Producer process has been terminated' in log
 if not (run/'summary.json').exists():report['status']='failed_or_incomplete';reports.append(report);continue
 summary=json.loads((run/'summary.json').read_text());report.update(summary)
 manifest=json.loads((run/'manifest.json').read_text());config=yaml.safe_load((run/'effective-config.yaml').read_text());report['sensor']=config['Dataset']['sensor_type'];report['preset']=manifest.get('preset');report['input_fps']=manifest.get('input_fps',0)
 report['metric_unit']='unverified Unity world unit' if run.name.startswith('medical-') else 'meter'
 snapshot=B/'源码快照'/(run.name+'.py');report['source_snapshot_verified']=snapshot.exists() and hashlib.sha256(snapshot.read_bytes()).hexdigest()==manifest['wrapper_sha256']
 report['config_hash_verified']=hashlib.sha256((run/'effective-config.yaml').read_bytes()).hexdigest()==manifest['config_sha256']
 records=[json.loads(line) for line in (run/'frames.jsonl').read_text().splitlines()];report['frame_records']=len(records);report['contiguous_frames']=[r['frame'] for r in records]==list(range(1,summary['frames']))
 fps=re.findall(r'Total FPS ([0-9.eE+-]+)',log);report['official_fps']=float(fps[-1]) if fps else None
 if len(records)>1:
  report['post_first_tracking_fps']=(len(records)-1)/(records[-1]['wall_seconds']-records[0]['wall_seconds'])
  report['tracking_ms_p50_p95']=(np.percentile([r['tracking_seconds']*1000 for r in records],[50,95])).tolist()
 if records and 'arrival_to_tracking_complete_seconds' in records[0]:
  ages=np.array([r['arrival_to_tracking_complete_seconds'] for r in records]);report['arrival_to_tracking_ms_p50_p95']=(np.percentile(ages*1000,[50,95])).tolist();report['final_backlog_seconds']=float(ages[-1]);report['latency_pass_200ms']=bool(np.percentile(ages,95)<=.2)
 plypath=run/'point_cloud'/'final'/'point_cloud.ply'
 report['ply_exists']=plypath.exists()
 if plypath.exists():
  ply=PlyData.read(str(plypath))['vertex'].data;report['ply_count']=len(ply);report['ply_finite']=all(np.isfinite(ply[n]).all() for n in ply.dtype.names)
 keyfile=run/'plot'/'stats_final.json';report['keyframe_ate']=json.loads(keyfile.read_text())['rmse'] if keyfile.exists() else None
 allfile=run/'all-frame-poses.json'
 if allfile.exists():
  rows=json.loads(allfile.read_text());gt=np.array([r['reference_c2w'] for r in rows]);est=np.array([r['estimated_c2w'] for r in rows]);reference=PosePath3D(poses_se3=gt);estimated=align_trajectory(PosePath3D(poses_se3=est),reference,correct_scale=report['sensor']=='monocular');errors=np.linalg.norm(estimated.positions_xyz-reference.positions_xyz,axis=1)
  report['all_frame_ate_rmse']=float(np.sqrt(np.mean(errors**2)));report['all_frame_pose_count']=len(rows);report['alignment']='Sim(3)' if report['sensor']=='monocular' else 'SE(3)'
  try:
   timestamps=np.array([float(Path(r['image_path']).stem) for r in rows]);rpe=[]
   for i,t in enumerate(timestamps):
    j=int(np.argmin(np.abs(timestamps-(t+1))))
    if j<=i or abs(timestamps[j]-t-1)>.05:continue
    dr=np.linalg.inv(gt[i])@gt[j];de=np.linalg.inv(estimated.poses_se3[i])@estimated.poses_se3[j];e=np.linalg.inv(dr)@de;rpe.append(np.linalg.norm(e[:3,3]))
   if rpe:report['rpe_1second_rmse']=float(np.sqrt(np.mean(np.square(rpe))));report['rpe_1second_pairs']=len(rpe)
  except ValueError:report['metric_unit']='Unverified Unity world unit; not metric clinical accuracy'
 report['status']='passed_development' if report['launcher_exit']==0 and not report['traceback'] and report['backend_returned'] and report['config_hash_verified'] and report['source_snapshot_verified'] and report['contiguous_frames'] and report.get('ply_finite') else 'partial_or_invalid'
 (run/'experiment-audit.json').write_text(json.dumps(report,indent=2));reports.append(report)
(B/'实验汇总.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
