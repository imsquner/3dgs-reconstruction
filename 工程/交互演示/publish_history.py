"""Publish a verified completed snapshot run; never launches reconstruction.
Run in the existing WSL environment. Full publication requires frozen source manifest.
"""
from pathlib import Path
import argparse,json,hashlib,os,time,shutil
import cv2,numpy as np
WEB=Path(__file__).resolve().parent
TASK=WEB.parent/'GSICP历史快照'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic(path,data):
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)

def input_path(value):
 if os.name=='nt':
  if value.startswith('/mnt/') and len(value)>7 and value[6]=='/':return Path(value[5].upper()+':'+value[6:])
  if value.startswith('/'):return Path('//wsl.localhost/Ubuntu-22.04'+value)
 return Path(value)

def publish_input_frames(run,manifest_path,dataset):
 cv2.setNumThreads(2)
 if shutil.disk_usage(WEB).free<15*1024**3:raise OSError('15GiB disk reserve')
 run=Path(run);manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
 out=WEB/'assets/history-published'/dataset/run.name;index=out/'index.json';meta=json.loads(index.read_text(encoding='utf-8'))
 if manifest['dataset']!=dataset or meta['run_id']!=run.name or meta.get('input_manifest_sha256')!=digest(Path(manifest_path)):raise ValueError('Input publication identity or frozen manifest mismatch')
 rows=[r for r in manifest['rows'] if not r['heldout']]
 records=[json.loads(line) for line in (run/'frames.jsonl').read_text().splitlines()]
 if len(rows)!=manifest['training_frames'] or len(rows)!=len(records) or meta['indices']!=[r['source_frame'] for r in rows]:raise ValueError('Incomplete actual training input sequence')
 previews=out/'input-frames-v1';previews.mkdir(exist_ok=True);published=[];started=time.monotonic()
 scale=5000 if dataset=='tum' else 6553.5
 for i,(row,record) in enumerate(zip(rows,records)):
  if i%100==0 and shutil.disk_usage(WEB).free<15*1024**3:raise OSError('15GiB disk reserve')
  if row['training_frame']!=i or record['frame']!=i:raise ValueError('Input training order mismatch')
  raw={key:input_path(row[key]).read_bytes() for key in ['rgb','depth']}
  if any(hashlib.sha256(raw[key]).hexdigest()!=row[key+'_sha256'] for key in raw):raise ValueError('Original input hash mismatch')
  rgb=cv2.imdecode(np.frombuffer(raw['rgb'],np.uint8),cv2.IMREAD_COLOR);depth=cv2.imdecode(np.frombuffer(raw['depth'],np.uint8),cv2.IMREAD_UNCHANGED)
  if rgb is None or depth is None or depth.dtype!=np.uint16 or rgb.shape[:2]!=depth.shape:raise ValueError('Invalid paired RGB/depth')
  width=min(rgb.shape[1],384);height=round(rgb.shape[0]*width/rgb.shape[1])
  rgb=cv2.resize(rgb,(width,height),interpolation=cv2.INTER_AREA)
  small=cv2.resize(depth,(width,height),interpolation=cv2.INTER_NEAREST)
  heat=cv2.applyColorMap(np.uint8(np.clip(small.astype(float)/scale/6,0,1)*255),cv2.COLORMAP_TURBO);heat[small==0]=80
  n=row['source_frame'];paths={'rgb':previews/f'{n}-rgb.jpg','depth':previews/f'{n}-depth.png'}
  for key,img,ext,options in [('rgb',rgb,'.jpg',[cv2.IMWRITE_JPEG_QUALITY,88]),('depth',heat,'.png',[cv2.IMWRITE_PNG_COMPRESSION,3])]:
   ok,encoded=cv2.imencode(ext,img,options)
   if not ok:raise ValueError('Input preview encode failed')
   data=encoded.tobytes()
   if not paths[key].exists() or paths[key].read_bytes()!=data:paths[key].write_bytes(data)
  published.append(dict(source_frame=n,training_frame=i,scene_time_seconds=row.get('scene_time_seconds'),schedule_time_seconds=n/meta['input_fps'],rgb=paths['rgb'].relative_to(WEB).as_posix(),depth=paths['depth'].relative_to(WEB).as_posix(),input_rgb_sha256=row['rgb_sha256'],input_depth_sha256=row['depth_sha256'],estimated_c2w=record['estimated_c2w']))
  if i%100==0 or i==len(rows)-1:print('INPUT_PREVIEWS',dataset,i+1,len(rows),'elapsed',round(time.monotonic()-started,1),'eta',round((time.monotonic()-started)/(i+1)*(len(rows)-i-1),1),flush=True)
 meta.update(input_frames=published,player_schema=2,input_preview_width=384)
 atomic(index,meta);print('INPUT_FRAMES_PUBLISHED',dataset,len(published),flush=True);return meta
def publish(run,manifest_path,dataset,scope):
 run=Path(run).resolve();run.relative_to((TASK/'运行').resolve())
 source=json.loads((run/'snapshot-index.json').read_text()); clock=json.loads((run/'input-clock.json').read_text()); manifest=json.loads(Path(manifest_path).read_text()); frames=[json.loads(line) for line in (run/'frames.jsonl').read_text().splitlines()]
 summary=json.loads((run/'summary.json').read_text());assert summary['frames']==len(frames) and summary['worker_exitcodes']==[0,0],'run did not finish successfully'
 audit=json.loads((run/'reload-audit.json').read_text());assert audit['status']=='passed' and audit['training_observations']==len(frames),'independent reload not passed'
 snapshots=source['snapshots']; assert snapshots and snapshots[-1]['final'],'missing final snapshot'
 assert len(frames)==len(clock['source_indices']) and all(frames[i]['frame']==i for i in range(len(frames)))
 assert manifest['dataset']==dataset,'dataset mismatch'
 inputs={r['source_frame']:r for r in manifest['rows']}; expected=[r['source_frame'] for r in manifest['rows'] if not r['heldout']]
 if scope=='full':
  assert len(clock['source_indices'])==manifest['training_frames'] and clock['source_indices']==expected,'incomplete full run'
  assert manifest['source_frames']==(2515 if dataset=='tum' else 2000),'wrong full protocol'
 else:assert len(frames)==30,'smoke publication must have exactly 30 training observations'
 label='完整重建' if scope=='full' else '初测30帧'
 out=WEB/'assets/history-published'/dataset/run.name;out.mkdir(parents=True,exist_ok=True)
 rows=[]; previous=-1
 for row in snapshots:
  n=row['source_frame']; ti=row['training_frame']; assert n>=previous;previous=n
  assert clock['source_indices'][ti]==n and not inputs[n]['heldout']
  assert row['source_keyframes'][-1]==n and len(row['keyframe_c2w'])==len(row['source_keyframes'])
  assert all(k<=n for k in row['source_keyframes']),'future trajectory leak'
  ply=(run/row['ply']).resolve();ply.relative_to(run);assert ply.is_file() and digest(ply)==row['sha256']
  item=inputs[n];rgb=Path(item['rgb']);depth=Path(item['depth'])
  assert digest(rgb)==item['rgb_sha256'] and digest(depth)==item['depth_sha256'],'input hash mismatch'
  image=cv2.imread(str(depth),cv2.IMREAD_UNCHANGED);color=cv2.imread(str(rgb));assert image is not None and color is not None
  scale=5000 if dataset=='tum' else 6553.5
  heat=cv2.applyColorMap(np.uint8(np.clip(image.astype(float)/scale/6,0,1)*255),cv2.COLORMAP_TURBO);heat[image==0]=80
  assert cv2.imwrite(str(out/f'{n}-rgb.jpg'),color,[cv2.IMWRITE_JPEG_QUALITY,92]);assert cv2.imwrite(str(out/f'{n}-depth.png'),heat)
  url=out.relative_to(WEB).as_posix();rows.append({**row,'ply':f'/history/{dataset}/{row["ply"]}','rgb':f'{url}/{n}-rgb.jpg','depth':f'{url}/{n}-depth.png','input_rgb_sha256':item['rgb_sha256'],'input_depth_sha256':item['depth_sha256'],'scene_time_seconds':item.get('scene_time_seconds'),'schedule_time_seconds':item.get('schedule_time_seconds'),'scene_time_basis':item.get('scene_time_basis')})
 base=WEB/'assets'/('replica.json' if dataset=='replica' else 'natural/tum-comparison/GSICP10.json');meta=json.loads(base.read_text());fps=clock['input_fps'];meta.update(snapshots=rows,run_id=run.name,scope=scope,history_scope_label=label,input_manifest_sha256=digest(Path(manifest_path)),input_fps=fps,indices=clock['source_indices'],duration=clock['source_indices'][-1]/fps,poses=[f['estimated_c2w'] for f in frames],gaussians=rows[-1]['gaussians'],kind='GS-ICP SLAM · '+label,bounds='',display_info=label,tracking_text='已完成',ate_text='—',show_rgb_preview=False)
 # Axis explicitly remains delivery schedule; original scene timestamps are independent evidence.
 meta['history_time_basis']='source index / delivery fps';meta.pop('frame_times',None)
 atomic(out/'index.json',meta)
 registry_path=WEB/'assets/history-publications.json';registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
 registry[dataset]={'run_id':run.name,'index':(out/'index.json').relative_to(WEB).as_posix(),'scope':scope,'input_manifest_sha256':digest(Path(manifest_path))}
 atomic(registry_path,registry)
 print(json.dumps({'dataset':dataset,'scope':scope,'run':run.name,'snapshots':len(rows),'index':str(out/'index.json')},ensure_ascii=False),flush=True)
 return meta
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--manifest',required=True);p.add_argument('--dataset',choices=['tum','replica'],required=True);p.add_argument('--scope',choices=['smoke','full'],default='full');p.add_argument('--inputs-only',action='store_true');a=p.parse_args()
 if a.inputs_only:publish_input_frames(a.run,a.manifest,a.dataset)
 else:publish(a.run,a.manifest,a.dataset,a.scope)
