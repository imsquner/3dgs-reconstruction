import {createHistoryPlayback,loadHistoryInput,loadHistoryMap,createPreparedHistorySlot,installPreparedHistoryArrays,loadPreparedHistoryPresentation} from './history-map.mjs';
import {parseMedicalMesh} from './assets/medical/mesh-loader.mjs';
import * as THREE from 'three';
import {Viewer,SplatBuffer,SceneRevealMode,LogLevel} from 'gs';
import {OrbitControls} from './vendor/OrbitControls.js';
import {cameraFromPose,sourceIndexAt,boundedTime} from './timeline.mjs';
import {controlAvailability} from './ui-state.mjs';
import {nativeLoadPromise} from './loader-bridge.mjs';
import {datasetsFor,datasetLabel,findSequence,selectCatalog,selectionCaption,sequenceGroups,presentationName} from './catalog.mjs';
import {officeVersions,resolveVersion} from './experiment-versions.mjs';
import {lookDirection} from './first-person.mjs';

const $=id=>document.getElementById(id),stage=$('stage');
function buttonText(id,text){const node=$(id);(node.querySelector('span')||node).textContent=text;if(id==='fullscreen')node.setAttribute('aria-label',text);}
$('fullscreen').setAttribute('aria-label','全屏');$('clean').setAttribute('aria-label','录屏视图');
const renderer=new THREE.WebGLRenderer({antialias:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1);renderer.setClearColor(0x151e24,1);stage.appendChild(renderer.domElement);
const camera=new THREE.PerspectiveCamera(60,1,.02,200);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.12;
function hoverEnabled(){return $('hoverRotate').checked;}
function pointerLocked(){return document.pointerLockElement===renderer.domElement;}
function hoverHint(){controls.enableRotate=false;controls.enableDamping=!pointerLocked();$('viewTip').textContent=pointerLocked()?'WASD 移动 · 空格上升 · Shift 下降 · 鼠标转向 · Esc 退出':hoverEnabled()?'点击地图进入 · WASD 移动 · 空格上升 · Shift 下降 · Esc 退出':'点击地图后 WASD 移动 · 空格上升 · Shift 下降 · 左键拖动转向';stage.dataset.pointerLocked=String(pointerLocked());}
function exitMouse(){if(pointerLocked())document.exitPointerLock();}
function lockFailure(error){$('hoverRotate').checked=false;hoverHint();stage.dataset.pointerLockError=error?.name||'pointerlockerror';$('viewTip').textContent='WASD 移动 · 空格上升 · Shift下降 · 左键拖动转向（当前浏览器未允许鼠标锁定）';}
renderer.domElement.addEventListener('click',async e=>{
 if(e.button!==0||!hoverEnabled()||!mapReady||loading||following||pointerLocked())return;
 try{await renderer.domElement.requestPointerLock();}catch(e){lockFailure(e);}
});
document.addEventListener('pointerlockchange',()=>{moveKeys.clear();hoverHint();});
document.addEventListener('pointerlockerror',()=>lockFailure());
document.addEventListener('mousemove',e=>{
 if(!pointerLocked()||!mapReady||loading||following||!controls.enabled||e.buttons!==0)return;
 const dx=e.movementX,dy=e.movementY;if(!Number.isFinite(dx)||!Number.isFinite(dy))return;
 turnView(dx,dy);
});
function turnView(dx,dy){
 const position=camera.position.clone(),distance=Math.max(position.distanceTo(controls.target),.0001);
 const direction=lookDirection(camera.getWorldDirection(new THREE.Vector3()).toArray(),camera.up.toArray(),dx,dy);
 controls.target.copy(position).add(new THREE.Vector3(...direction).multiplyScalar(distance));
 camera.lookAt(controls.target);camera.updateMatrixWorld(true);
}
let lookDrag=null;
renderer.domElement.addEventListener('pointerdown',e=>{if(e.button===0&&!hoverEnabled()&&mapReady&&!following&&!controls.enableRotate)lookDrag={x:e.clientX,y:e.clientY};});
document.addEventListener('pointermove',e=>{if(!lookDrag||pointerLocked()||following||loading)return;if(!(e.buttons&1)){lookDrag=null;return;}turnView(e.clientX-lookDrag.x,e.clientY-lookDrag.y);lookDrag={x:e.clientX,y:e.clientY};});
document.addEventListener('pointerup',()=>{lookDrag=null;});
window.addEventListener('blur',()=>{lookDrag=null;});
$('hoverRotate').onchange=()=>{exitMouse();hoverHint();};
hoverHint();
const threeScene=new THREE.Scene();
let mesh;
let viewer,scene,line,cursor,observations,accumulation,contentMode='gs',playing=false,following=false,time=0,last=performance.now(),saved=null,token=0,loading=false,lastInput='';
let historyLoader=null,historyVersion=null,historyRequested=null;
let historyPlayback=null,historyFrame=null,historyRetiring=Promise.resolve(),historyMapSlot=null,historyInputs=new Map();let historyWorker=null,historyWorkerSerial=0,historyWorkerJobs=new Map();
let fpsStart=performance.now(),frames=0;
let mapReady=false,lastSceneId='replica',versionNumber='00';
function effectiveEntry(id=lastSceneId){return {...findSequence(id).sequence,...(resolveVersion(id,versionNumber)||{})};}
function versionUI(){const v=resolveVersion(lastSceneId,versionNumber);$('experimentPanel').hidden=!v;$('experimentVersion').replaceChildren(...officeVersions.map(x=>new Option(x.number+' · '+x.label,x.number)));$('experimentVersion').value=versionNumber;for(const n of ['02','04'])$('compare'+n).setAttribute('aria-pressed',String(versionNumber===n));}
async function chooseVersion(n){if(loading||lastSceneId!=='office'||n===versionNumber)return;const view={position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone(),time};versionNumber=n;contentMode='gs';$('contentMode').value='gs';await load('office',view);}
$('experimentVersion').onchange=e=>chooseVersion(e.target.value);$('compare02').onclick=()=>chooseVersion('02');$('compare04').onclick=()=>chooseVersion('04');
function timelineInteractive(){return !!scene&&scene.poses.length>1&&scene.duration>0;}
function lockControls(){const a=controlAvailability({loading,ready:mapReady,saved:!!saved,mode:contentMode});for(const id of ['category','dataset','scene','experimentVersion','compare02','compare04'])$(id).disabled=loading;$('contentMode').disabled=!a.mode;$('modeGs').disabled=!a.mode||!effectiveEntry().assetKey;$('modePoints').disabled=!a.mode||!effectiveEntry().observations;$('modeHistory').disabled=!a.mode||!effectiveEntry().history;for(const id of ['free','follow','reset','overview','save','trajectory'])$(id).disabled=!a.map;$('play').disabled=!a.map||!timelineInteractive();$('seek').disabled=!a.map||!timelineInteractive();$('restore').disabled=!a.restore;controls.enabled=a.map&&!following;}
function catalogUI(id){const {dataset,sequence}=findSequence(id);$('category').value=dataset.category;document.querySelector('label[for=dataset]').textContent=dataset.category==='medical'?'技术方案':'数据集';document.querySelector('label[for=scene]').textContent=dataset.category==='medical'?'数据集 / 序列 / 结果版本':'具体序列';$('modeGs').querySelector('strong').textContent=dataset.id==='medical-tsdf'?'最终三角网格':'最终 3DGS';$('dataset').replaceChildren(...datasetsFor(dataset.category).map(d=>new Option(datasetLabel(d),d.id)));$('dataset').value=dataset.id;$('dataset').title=datasetLabel(dataset);const options=[];for(const group of sequenceGroups(dataset.sequences)){if(group.label){const optgroup=document.createElement('optgroup');optgroup.label=dataset.id==='loopsplat'?'LoopSplat':group.label;for(const s of group.sequences)optgroup.append(new Option(presentationName(s.id),s.id));options.push(optgroup);}else options.push(...group.sequences.map(s=>new Option(presentationName(s.id),s.id)));}$('scene').replaceChildren(...options);$('scene').value=sequence.id;$('scene').title=presentationName(sequence.id);$('datasetSummary').textContent=`${datasetLabel(dataset)} / ${sequence.summary}`;$('sequenceState').textContent=sequence.status;$('sequenceState').dataset.available=String(!!sequence.assetKey);$('contentMode').querySelector('option[value="history"]').disabled=!effectiveEntry(id).history;$('contentMode').querySelector('option[value="points"]').disabled=!effectiveEntry(id).observations;$('contentMode').querySelector('option[value="points"]').textContent=id==='ooosplat-office-balanced'?'COLMAP稀疏观测累计':'RGB-D观测累积';}
function chooseCatalog(selection){if(loading){catalogUI(lastSceneId);return;}const {sequence}=selectCatalog(selection);const previous=effectiveEntry();const preserved=mapReady&&sequence.comparisonGroup&&previous.comparisonGroup===sequence.comparisonGroup?{position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone(),time}:null;versionNumber='00';if((contentMode==='history'&&!sequence.history)||(!sequence.observations&&contentMode==='points')){contentMode='gs';$('contentMode').value='gs';}load(sequence.id,preserved);}
function modeUI(){const entry=effectiveEntry();$('modeHistory').setAttribute('aria-pressed',String(contentMode==='history'));$('modeGs').setAttribute('aria-pressed',String(contentMode==='gs'));$('modePoints').setAttribute('aria-pressed',String(contentMode==='points'));$('modePoints').querySelector('small').textContent=entry.id==='ooosplat-office-balanced'?'RGB＋COLMAP稀疏观测回放':'真实 RGB-D 随输入增加';$('modePoints').title=entry.observations?'切换到本场景观测累计':'本序列尚未提供观测累积资产';$('modeNote').textContent='';}
function status(text,progress=null,error=false){$('status').hidden=false;$('status').classList.remove('empty');$('statusLabel').textContent=text;$('status').classList.toggle('error',error);$('retry').hidden=!error;$('loadProgress').hidden=error;if(progress===null)$('loadProgress').removeAttribute('value');else $('loadProgress').value=progress;$('statusHint').textContent=error?'检查本地服务与模型文件后重试':'读取和整理本地模型，完成后即可移动视角';}
async function getAsset(path,type='json'){let r;try{r=await fetch(path);}catch(e){throw new Error(`本地服务连接中断（${path}）`);}if(!r.ok)throw new Error(`${path}（HTTP ${r.status}）`);return type==='json'?r.json():r.arrayBuffer();}
const trajectoryMaterial=new THREE.LineBasicMaterial({color:0x56dcc1,transparent:true,opacity:.8,depthTest:false});
function clock(t,precision=0){const scale=10**precision,units=Math.round(t*scale),wholeSeconds=Math.floor(units/scale),fraction=precision?`.${String(units%scale).padStart(precision,'0')}`:'';return `${Math.floor(wholeSeconds/60).toString().padStart(2,'0')}:${String(wholeSeconds%60).padStart(2,'0')}${fraction}`;}
function resize(){
 const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;
 if(scene){const [W,H,fx,fy,cx,cy]=scene.intrinsic;camera.fov=2*Math.atan(H/(2*fy))*180/Math.PI;camera.updateProjectionMatrix();camera.projectionMatrix.elements[0]*=fx/fy;camera.projectionMatrix.elements[8]=-(2*cx+1-W)/H/camera.aspect;camera.projectionMatrix.elements[9]=(2*cy+1-H)/H;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();}
 else camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);
function setPose(p){const c=cameraFromPose(p);camera.position.fromArray(c.position);camera.up.fromArray(c.up);controls.target.fromArray(c.position).add(new THREE.Vector3().fromArray(c.forward).multiplyScalar(1.2));camera.lookAt(controls.target);controls.update();camera.updateMatrixWorld(true);}
function setFollow(value){if(value)exitMouse();following=value;if(!value&&scene){camera.up.fromArray(cameraFromPose(scene.poses[0]).up);camera.lookAt(controls.target);}$('follow').setAttribute('aria-pressed',String(value));$('free').setAttribute('aria-pressed',String(!value));controls.enabled=!value;$('follow').classList.toggle('active',value);$('free').classList.toggle('active',!value);$('stageLabel').textContent=selectionCaption(lastSceneId)+(lastSceneId==='office'?' · 版本'+versionNumber:'')+' · '+(contentMode==='history'?'高斯建图过程 · '+(scene?.history_scope_label||'初测30帧'):contentMode==='points'?'观测累积':scene?.representation==='mesh'?'最终网格':'最终3DGS')+' · '+(value?'轨迹回放':'自由视角');if(value)syncTime();}
function syncTime(){if(!scene)return;if(contentMode==='history'){syncHistory();return;}const i=sourceIndexAt(time,scene.input_fps,scene.indices,scene.frame_times);$('seek').value=time;$('elapsed').textContent=clock(time,scene.time_precision||0);$('frame').textContent=`源帧 ${scene.indices[i]} / ${scene.indices.at(-1)} · 轨迹位姿 ${i+1} / ${scene.poses.length}`;line?.geometry.setDrawRange(0,i+1);if(cursor)cursor.position.fromArray(cameraFromPose(scene.poses[i]).position);if(following)setPose(scene.poses[i]);if(contentMode==='points'&&accumulation&&observations){const k=sourceIndexAt(time,accumulation.input_fps||5,accumulation.chunks.map(c=>c.source_frame),accumulation.frame_times||(scene.offline?accumulation.chunks.map(c=>c.time_seconds):null)),chunk=accumulation.chunks[k];observations.geometry.setDrawRange(0,chunk.point_count);$('count').textContent=chunk.point_count.toLocaleString()+' 观测点';if(lastInput!==chunk.input_image){$('inputImage').src=chunk.input_image;lastInput=chunk.input_image;}const dep=chunk.depth_image,di=$('inputDepth');$('inputCaption').textContent=(dep?'RGB／Depth':'RGB')+' · 帧 '+chunk.source_frame;if(dep){if(di.getAttribute('src')!==dep)di.src=dep;di.hidden=false;di.alt='当前输入帧深度（固定0–100mm，深灰为无效）';}else di.hidden=true;}else if(scene.show_rgb_preview&&scene.rgb_images?.[i]){const image=scene.rgb_images[i];if(lastInput!==image){$('inputImage').src=image;lastInput=image;}$('inputCaption').textContent=`RGB · 帧 ${scene.indices[i]}`;}}
function syncHistory(){
 if(!historyPlayback)return;
 const state=historyPlayback.state;time=state.time;
 $('seek').value=time;$('elapsed').textContent=clock(time,1);
 stage.dataset.historyLoading=String(state.busy);stage.dataset.historyBuffering=String(state.busy);
 if(state.failed)return;
 if(historyFrame&&historyVersion){
  $('frame').textContent=(state.busy?'缓冲 · ':'')+`源帧 ${historyFrame.source_frame} · 地图帧 ${historyVersion.source_frame} · 版本 ${historyVersion.snapshot_id}`;
  if(following)setPose(historyFrame.estimated_c2w);
 }
 if(state.done&&playing)setPlay(false);
}
function adoptHistoryImage(id,image){const old=$(id);for(const a of old.attributes)if(a.name!=='src')image.setAttribute(a.name,a.value);old.replaceWith(image);}
async function disposeHistoryPayload(payload){if(payload?.candidate)await payload.candidate.dispose();}
function historyInput(row){
 let promise=historyInputs.get(row.source_frame);if(!promise){promise=loadHistoryInput(row);promise.catch(()=>{});historyInputs.set(row.source_frame,promise);}return promise;
}
function warmHistory(){
 if(!historyPlayback||!playing)return;const state=historyPlayback.state;if(state.busy||state.failed)return;
 const next=scene.snapshots[state.mapIndex+1];if(next)historyMapSlot?.warm(next.snapshot_id);
 const upcoming=scene.input_frames.slice(state.frameIndex+1,state.frameIndex+9),keys=new Set(upcoming.map(r=>r.source_frame));
 for(const key of historyInputs.keys())if(!keys.has(key))historyInputs.delete(key);
 for(const row of upcoming)historyInput(row);
}
function decodeHistory(row){
 if(!historyWorker){historyWorker=new Worker('/assets/history-worker.mjs',{type:'module'});historyWorker.onmessage=({data})=>{const job=historyWorkerJobs.get(data.id);if(!job)return;historyWorkerJobs.delete(data.id);data.error?job.reject(Error(data.error)):job.resolve(data);};historyWorker.onerror=e=>{historyWorker?.terminate();historyWorker=null;for(const job of historyWorkerJobs.values())job.reject(Error(e.message));historyWorkerJobs.clear();};}
 return new Promise((resolve,reject)=>{const id=++historyWorkerSerial;historyWorkerJobs.set(id,{resolve,reject});historyWorker.postMessage({id,row});});
}
async function buildHistoryMap(id,isCurrent){
 const row=scene.snapshots.find(r=>r.snapshot_id===id),perf={version:id,started:performance.now()};
 const prepared=await decodeHistory(row);perf.readMs=prepared.readMs;perf.workerMs=prepared.workerMs;
 if(!isCurrent())return null;await historyRetiring;if(!isCurrent())return null;
 const buffer=installPreparedHistoryArrays(new SplatBuffer(prepared.buffer),prepared);let candidate;
 try{
  candidate=new Viewer({selfDrivenMode:false,renderer,camera,threeScene,useBuiltInControls:false,gpuAcceleratedSort:false,enableSIMDInSort:true,sharedMemoryForWorkers:crossOriginIsolated,integerBasedSort:false,halfPrecisionCovariancesOnGPU:false,sphericalHarmonicsDegree:row.sh_degree,optimizeSplatData:false,sceneRevealMode:SceneRevealMode.Instant,logLevel:LogLevel.None,ignoreDevicePixelRatio:true});
    const mapMesh=candidate.splatMesh;
  mapMesh.getDataForDistancesComputation=(from,to)=>({centers:prepared.paddedCenters.subarray(from*4,(to+1)*4),sceneIndexes:prepared.sceneIndexes.subarray(from,to+1)});
  mapMesh.updateVisibleRegion=()=>{mapMesh.calculatedSceneCenter.fromArray(prepared.center);mapMesh.material.uniforms.sceneCenter.value.copy(mapMesh.calculatedSceneCenter);mapMesh.maxSplatDistanceFromSceneCenter=mapMesh.visibleRegionRadius=mapMesh.visibleRegionBufferRadius=prepared.radius;mapMesh.updateVisibleRegionFadeDistance(SceneRevealMode.Instant);};
  await candidate.addSplatBuffers([buffer],[{splatAlphaRemovalThreshold:0}],false,false,false);
  await renderer.compileAsync(mapMesh,camera,threeScene);
  for(const item of Object.values(mapMesh.splatDataTextures)){if(item.texture){renderer.initTexture(item.texture);await new Promise(requestAnimationFrame);}}
  if(!candidate.splatRenderReady)throw Error('地图尚未准备完成');
  perf.readyMs=performance.now()-perf.started;(window.historyPerf??=[]).push(perf);if(window.historyPerf.length>500)window.historyPerf.shift();return {candidate};
 }catch(error){try{await candidate?.dispose();}catch{}throw error;}finally{}
}
async function prepareHistory(target,isCurrent){
 stage.dataset.historyTarget=String(target.map.snapshot_id);
 const payload=await loadPreparedHistoryPresentation(target.inputChanged?historyInput(target.input):null,target.mapChanged?historyMapSlot.take(target.map.snapshot_id):null,disposeHistoryPayload);
 if(!isCurrent()){await disposeHistoryPayload(payload);return {};}
 return payload;
}
function presentHistory(payload,target){
 delete stage.dataset.historyFailed;
 const row=target.map;
 if(payload.candidate){
  const old=viewer;viewer=payload.candidate;payload.candidate=null;
  historyRetiring=old?old.dispose().catch(error=>console.warn('History retired viewer cleanup',error)):Promise.resolve();
  if(line){threeScene.remove(line);line.geometry.dispose();}
  line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(row.keyframe_c2w.map(p=>new THREE.Vector3(...cameraFromPose(p).position))),trajectoryMaterial);line.renderOrder=20;line.visible=$('trajectory').checked;threeScene.add(line);
 }
 historyVersion=row;historyRequested=row.snapshot_id;historyFrame=target.input;
 if(payload.input){adoptHistoryImage('inputImage',payload.input.images[0]);adoptHistoryImage('inputDepth',payload.input.images[1]);}
 $('inputDepth').hidden=false;$('inputCaption').textContent=`RGB / Depth · 源帧 ${target.input.source_frame}`;
 $('count').textContent=row.gaussians.toLocaleString();
 stage.dataset.historyVersion=String(row.snapshot_id);stage.dataset.historySource=String(row.source_frame);stage.dataset.historyInput=String(target.input.source_frame);
 if(cursor)cursor.position.fromArray(cameraFromPose(target.input.estimated_c2w).position);
 if(following)setPose(target.input.estimated_c2w);
 camera.updateMatrixWorld(true);
 window.dispatchEvent(new CustomEvent('history-present',{detail:{mode:target.mode,source:target.input.source_frame,training:target.input.training_frame,version:row.snapshot_id,mapSource:row.source_frame,mapChanged:target.mapChanged,inputChanged:target.inputChanged,count:row.gaussians,time:target.time}}));
}
function setPlay(value){playing=value;$('play').setAttribute('aria-pressed',String(value));buttonText('play',value?'暂停':'播放');$('play').querySelector('img').src=`vendor/icons/${value?'pause':'play'}.svg`;}
function overview(){if(!scene)return;setFollow(false);const box=observations?.geometry.boundingBox||(scene.map_bounds?new THREE.Box3(new THREE.Vector3(...scene.map_bounds[0]),new THREE.Vector3(...scene.map_bounds[1])):new THREE.Box3().setFromPoints(scene.poses.map(p=>new THREE.Vector3(...cameraFromPose(p).position)))),center=box.getCenter(new THREE.Vector3()),size=Math.max(box.getSize(new THREE.Vector3()).length(),.1);camera.position.copy(center).add(new THREE.Vector3(size*.53,-size*.53,size*.43));camera.up.copy(new THREE.Vector3(...cameraFromPose(scene.poses[0]).up));controls.target.copy(center);camera.lookAt(center);controls.update();camera.updateMatrixWorld(true);}
async function load(id,preserved=null){
 if(loading)return;exitMouse();const entry=effectiveEntry(id);if(contentMode==='history'&&!entry.history){contentMode='gs';$('contentMode').value='gs';}catalogUI(id);loading=true;mapReady=false;lastSceneId=id;versionUI();delete stage.dataset.loadedVersion;delete stage.dataset.loadedScene;delete stage.dataset.loadedMode;const ticket=++token;setPlay(false);lockControls();modeUI();status('读取场景与轨迹');$('stageLabel').textContent=selectionCaption(id)+' · 地图未就绪';$('frame').textContent='源帧 —';$('elapsed').textContent='—';$('duration').textContent='—';$('boundary').textContent='地图未就绪，请等待加载或重试。';$('seek').max=1;$('seek').value=0;$('countLabel').textContent=contentMode==='points'?'累计观测点':scene?.representation==='mesh'?'网格规模':'高斯数量';$('inputPreview').hidden=true;for(const field of ['kind','count','tracking','ate'])$(field).textContent='—';
 try{
  await clearMap();
  scene=null;time=0;setFollow(false);
  if(!entry.assetKey){status(entry.status);$('status').classList.add('empty');$('loadProgress').hidden=true;$('statusHint').textContent='该序列暂未提供可浏览地图，可选择其他序列。';$('stageLabel').textContent=selectionCaption(id)+' · '+entry.status;$('boundary').textContent=entry.summary+'；'+entry.status+'。各序列地图独立保存，当前没有加载其他序列的地图。';window.dispatchEvent(new Event('catalog-empty'));return;}
  scene=await getAsset(contentMode==='history'?entry.history:`assets/${entry.assetKey}.json`);if(ticket!==token)return;
  time=0;saved=preserved?.saved||null;$('restore').disabled=!saved;buttonText('save','保存当前视角');$('countLabel').textContent=contentMode==='points'?'累计观测点':scene?.representation==='mesh'?'网格规模':'高斯数量';
  camera.near=scene.near??(scene.label?.includes('医学')||scene.representation==='mesh'||id.startsWith('medgs-')?.0002:.02);camera.far=scene.far||200;resize();setPose(scene.poses[0]);
  if(contentMode==='history'){
   if(!scene.input_frames?.length)throw Error('逐帧输入索引尚未准备完成');
   historyMapSlot=createPreparedHistorySlot({load:buildHistoryMap,dispose:disposeHistoryPayload});historyPlayback=createHistoryPlayback({frames:scene.input_frames,snapshots:scene.snapshots,fps:scene.input_fps,load:prepareHistory,commit:presentHistory,dispose:disposeHistoryPayload,onState:syncHistory,onError:error=>{setPlay(false);stage.dataset.historyFailed='true';$('frame').textContent=error.message;}});
   await historyPlayback.seek(preserved?.time||0);
   if(historyPlayback.state.failed)throw Error('历史地图或输入加载失败');
  }else if(contentMode==='gs'&&scene.representation==='mesh'){
   status('载入最终三角网格');const response=await fetch(scene.ply);if(!response.ok)throw Error('Mesh HTTP '+response.status);mesh=parseMedicalMesh(await response.text());threeScene.add(mesh);
  }else if(contentMode==='gs'){
   viewer=new Viewer({selfDrivenMode:false,renderer,camera,threeScene,useBuiltInControls:false,gpuAcceleratedSort:false,enableSIMDInSort:true,sharedMemoryForWorkers:crossOriginIsolated,integerBasedSort:false,halfPrecisionCovariancesOnGPU:false,sphericalHarmonicsDegree:scene.spherical_harmonics_degree??0,sceneRevealMode:SceneRevealMode.Instant,logLevel:LogLevel.None,ignoreDevicePixelRatio:true});
   status('载入最终高斯地图');await nativeLoadPromise(viewer.addSplatScene(scene.ply,{splatAlphaRemovalThreshold:scene.splat_alpha_threshold??1,showLoadingUI:false,progressiveLoad:false,onProgress:p=>status('载入与整理高斯地图',Number.isFinite(p)?p:null)}));
  }else{
   status('读取本场景观测记录');accumulation=await getAsset(scene.accumulation_path||'assets/office-accumulation.json');
   const [pb,cb]=await Promise.all([getAsset(scene.points_path||'assets/office-observations.xyz','binary'),getAsset(scene.colors_path||'assets/office-observations.rgb','binary')]);
   const positions=new Float32Array(pb),bytes=new Uint8Array(cb),colors=new Float32Array(bytes.length);
   for(let i=0;i<bytes.length;i++){const v=bytes[i]/255;colors[i]=v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4);}
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(positions,3));geo.setAttribute('color',new THREE.BufferAttribute(colors,3));geo.computeBoundingSphere();geo.computeBoundingBox();
   observations=new THREE.Points(geo,new THREE.PointsMaterial({size:scene.point_size??.013,vertexColors:true,sizeAttenuation:true}));threeScene.add(observations);
  }
  if(line){threeScene.remove(line);line.geometry.dispose();line=null;}const pts=(contentMode==='history'?historyVersion.keyframe_c2w:scene.poses).map(p=>new THREE.Vector3(...cameraFromPose(p).position));line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),trajectoryMaterial);line.renderOrder=20;threeScene.add(line);
  const scale=scene.marker_size??(id.startsWith('med')?.0005:id==='unity'?.006:.018);cursor=new THREE.Mesh(new THREE.SphereGeometry(scale,10,8),new THREE.MeshBasicMaterial({color:0xffc766,depthTest:false}));cursor.renderOrder=21;threeScene.add(cursor);
  document.querySelector('#ate').parentElement.querySelector('dt').textContent=scene.ate_label||'轨迹误差 ATE';$('trackingLabel').textContent=scene.tracking_label||(scene.offline?'处理方式':scene.experiment?'建图总耗时折算（含优化）':'原实验跟踪吞吐');$('kind').textContent=scene.kind.split(' · ')[0].replace('短测','');$('count').textContent=(contentMode==='history'?historyVersion.gaussians.toLocaleString():scene.representation==='mesh'?`${scene.vertices.toLocaleString()} 顶点 / ${scene.triangles.toLocaleString()} 面`:scene.gaussians.toLocaleString());$('tracking').textContent=scene.tracking_text||(scene.offline?'离线处理（非在线FPS）':Number.isFinite(scene.measured_tracking_fps)?scene.measured_tracking_fps.toFixed(2)+' FPS':'未记录');$('ate').textContent=scene.ate_text||(scene.ate_m===null||scene.ate_m===undefined?(entry.experimentGroup?'短测不报告轨迹精度':id.startsWith('med')?'未接入指标':'未评价（尺度未确认）'):(scene.ate_m*100).toFixed(2)+' cm');$('duration').textContent=clock(scene.duration,scene.time_precision||0);$('seek').step=contentMode==='history'||scene.frame_times?'any':'1';$('seek').max=scene.duration;$('boundary').textContent=contentMode==='points'?(scene.accumulation_description||'真实RGB-D＋记录的估计位姿，顺序累积观测点。每5帧/每6像素采样，1.5cm体素保留首次观测；不是历史3DGS地图，也不是本轮在线性能测量。'):scene.bounds;$('inputPreview').hidden=!(contentMode==='history'||contentMode==='points'||scene.show_rgb_preview);$('inputDepth').hidden=contentMode!=='history';
  $('inputRate').textContent=scene.offline?'真实时间戳':entry.experimentGroup?`${scene.input_fps} FPS`:`${scene.input_fps} FPS`; $('fixedView').replaceChildren(new Option('选择固定视角',''),...(scene.fixed_views||[]).map((v,i)=>new Option((v.kind==='offset-diagnostic'?'偏移诊断 ':'路径视角 ')+(i+1),i)));$('fixedView').disabled=!(scene.fixed_views?.length);$('offlineInfo').hidden=!(scene.offline||scene.display_info);$('offlineInfo').textContent=scene.display_info||(scene.offline?'2585张RGB · 总训练15000步 · 离线相机重建与训练 · 尺度未标定':'');$('observationVideo').hidden=!scene.observation_video;$('observationVideo').href=scene.observation_video||'#';setFollow(false);if(preserved){time=Math.min(preserved.time,scene.duration);camera.position.copy(preserved.position);camera.up.copy(preserved.up);controls.target.copy(preserved.target);controls.update();camera.updateMatrixWorld(true);}syncTime();if(contentMode==='history')cursor.position.fromArray(cameraFromPose(historyFrame.estimated_c2w).position);line.visible=cursor.visible=$('trajectory').checked;mapReady=true;stage.dataset.loadedScene=id;stage.dataset.loadedVersion=versionNumber;stage.dataset.loadedMode=contentMode;modeUI();if(contentMode==='history')$('modeHistory').querySelector('small').textContent=scene.history_scope_label||'初测30帧';if(scene.offline)$('modeNote').textContent=contentMode==='points'?scene.accumulation_description:scene.bounds;if(id.startsWith('med')){$('hoverRotate').checked=true;hoverHint();}const e=scene.offline?null:scene.experiment;$('experimentMetrics').textContent=scene.display_info||(e?`${id.startsWith("tum-")?scene.label:`版本${versionNumber}`} · ${e.frames}帧 · ${e.steps_per_frame}步/帧\n${e.metrics?`PSNR ${e.metrics.psnr_db.toFixed(2)} dB · SSIM ${e.metrics.ssim.toFixed(4)}`:`完整图像指标待评价；当前仅观察地图`}\n实验耗时 ${e.wall_seconds.toFixed(1)}秒`: '原始完整地图保留；不能与240帧短段作等范围量化对照。');$('status').hidden=true;if(contentMode==='history'&&!preserved)overview();window.dispatchEvent(new Event('scene-ready'));
 }catch(e){console.error(e);mapReady=false;await clearMap();scene=null;status('地图加载失败：'+e.message,null,true);}
 finally{loading=false;lockControls();}
}
async function clearMap(){
 await historyPlayback?.stop();historyPlayback=null;historyFrame=null;await historyMapSlot?.stop();historyMapSlot=null;historyInputs.clear();historyWorker?.terminate();historyWorker=null;historyWorkerJobs.clear();await historyRetiring;historyRetiring=Promise.resolve();await historyLoader?.stop();$('historyStill').hidden=true;$('historyStill').removeAttribute('src');historyLoader=null;historyVersion=null;historyRequested=null;$('inputDepth').hidden=true;$('inputDepth').removeAttribute('src');
 if(mesh){threeScene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;}
 const oldViewer=viewer;viewer=null;
 if(oldViewer){try{await oldViewer.dispose();}catch(e){console.warn('Viewer cleanup reported an error',e);}}
 if(observations){threeScene.remove(observations);observations.geometry.dispose();observations.material.dispose();observations=null;}
 if(line){threeScene.remove(line);line.geometry.dispose();line=null;}
 if(cursor){threeScene.remove(cursor);cursor.geometry.dispose();cursor.material.dispose();cursor=null;}
 accumulation=null;lastInput='';saved=null;$('inputImage').removeAttribute('src');$('fixedView').disabled=true;$('observationVideo').hidden=true;$('offlineInfo').hidden=true;moveKeys.clear();lookDrag=null;
}
$('category').onchange=e=>chooseCatalog({category:e.target.value});$('dataset').onchange=e=>chooseCatalog({category:$('category').value,datasetId:e.target.value});$('scene').onchange=e=>chooseCatalog({category:$('category').value,datasetId:$('dataset').value,sequenceId:e.target.value});$('contentMode').onchange=e=>{if(loading){e.target.value=contentMode;return;}if(e.target.value==='points'&&!effectiveEntry().observations){e.target.value=contentMode;return;}const view=mapReady?{position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone(),time,saved}:null;historyLoader?.cancel();contentMode=e.target.value;load(lastSceneId,view);};$('free').onclick=()=>setFollow(false);$('follow').onclick=()=>setFollow(true);
$('modeHistory').onclick=()=>{if(loading||contentMode==='history'||!effectiveEntry().history)return;$('contentMode').value='history';$('contentMode').dispatchEvent(new Event('change'));};
$('modeGs').onclick=()=>{if(loading||contentMode==='gs')return;$('contentMode').value='gs';$('contentMode').dispatchEvent(new Event('change'));};$('modePoints').onclick=()=>{if(loading||contentMode==='points')return;$('contentMode').value='points';$('contentMode').dispatchEvent(new Event('change'));};$('retry').onclick=()=>load(lastSceneId);
$('play').onclick=()=>{if(!scene||loading||!timelineInteractive())return;if(time>=scene.duration){time=0;if(contentMode==='history')void historyPlayback?.seek(0);}setPlay(!playing);};$('seek').oninput=e=>{if(!timelineInteractive())return;if(contentMode==='history'){setPlay(false);void historyPlayback?.seek(Number(e.target.value));}else{time=Number(e.target.value);syncTime();}};
$('reset').onclick=()=>{setPlay(false);time=0;setFollow(false);setPose(scene.poses[0]);if(contentMode==='history')void historyPlayback?.seek(0);else syncTime();};$('overview').onclick=overview;
$('save').onclick=()=>{saved={sceneId:lastSceneId,position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone()};$('restore').disabled=false;buttonText('save','视角已保存');};
$('restore').onclick=()=>{if(!saved||saved.sceneId!==lastSceneId)return;setFollow(false);camera.position.copy(saved.position);camera.up.copy(saved.up);controls.target.copy(saved.target);controls.update();};
$('fixedView').onchange=e=>{if(!scene||!mapReady||e.target.value==='')return;const v=scene.fixed_views[Number(e.target.value)];setPlay(false);setFollow(false);camera.position.fromArray(v.position);camera.up.fromArray(v.up);controls.target.fromArray(v.look_at);camera.lookAt(controls.target);controls.update();};
$('trajectory').onchange=e=>{if(line)line.visible=e.target.checked;if(cursor)cursor.visible=e.target.checked;};
function clean(){document.body.classList.toggle('clean');$('returnUI').hidden=!document.body.classList.contains('clean');resize();}
$('clean').onclick=clean;$('returnUI').onclick=clean;
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){buttonText('fullscreen','请按 F11 全屏');console.warn('Fullscreen unavailable',e);}};
document.addEventListener('fullscreenchange',()=>{buttonText('fullscreen',document.fullscreenElement?'退出全屏':'全屏');resize();});
function panel(value){document.body.classList.toggle('panel-hidden',!value);$('togglePanel').setAttribute('aria-expanded',String(value));$('togglePanel').setAttribute('aria-label',value?'收起控制面板':'展开控制面板');$('togglePanel').title=value?'收起控制面板':'展开控制面板';resize();}
$('togglePanel').onclick=()=>panel(document.body.classList.contains('panel-hidden'));
if(matchMedia('(max-width:700px)').matches)panel(false);
$('toggleInput').onclick=()=>{const collapsed=$('inputPreview').classList.toggle('collapsed');$('toggleInput').textContent=collapsed?'展开输入画面':'收起输入画面';$('toggleInput').setAttribute('aria-expanded',String(!collapsed));};
const moveKeys=new Set(),moveCodes=new Set(['KeyW','KeyA','KeyS','KeyD','Space','ShiftLeft','ShiftRight']);
renderer.domElement.tabIndex=0;
renderer.domElement.addEventListener('pointerdown',()=>renderer.domElement.focus({preventScroll:true}));
function navigationActive(){return mapReady&&!loading&&!following&&(pointerLocked()||document.activeElement===renderer.domElement);}
function moveCamera(dt){
 if(!navigationActive()){moveKeys.clear();return;}
 const up=camera.up.clone().normalize(),forward=camera.getWorldDirection(new THREE.Vector3()).normalize(),right=new THREE.Vector3(1,0,0).applyQuaternion(camera.quaternion).normalize();
 const movement=new THREE.Vector3().addScaledVector(forward,Number(moveKeys.has('KeyW'))-Number(moveKeys.has('KeyS'))).addScaledVector(right,Number(moveKeys.has('KeyD'))-Number(moveKeys.has('KeyA'))).addScaledVector(up,Number(moveKeys.has('Space'))-Number(moveKeys.has('ShiftLeft')||moveKeys.has('ShiftRight')));
 if(!movement.lengthSq())return;
 const bounds=scene.map_bounds,extent=scene.movement_extent||(bounds?new THREE.Vector3(...bounds[1]).sub(new THREE.Vector3(...bounds[0])).length():camera.position.distanceTo(controls.target));
 movement.normalize().multiplyScalar(Math.max(extent*.15,.0001)*Number($('moveSpeed').value)*Math.min(dt,.05));camera.position.add(movement);controls.target.add(movement);
}
document.addEventListener('keyup',e=>moveKeys.delete(e.code));
window.addEventListener('blur',()=>moveKeys.clear());
document.addEventListener('visibilitychange',()=>{if(document.hidden)moveKeys.clear();});
document.onkeydown=e=>{if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(e.target.tagName)||e.target.isContentEditable)return;if(e.key==='Escape'){moveKeys.clear();exitMouse();renderer.domElement.blur();return;}if(navigationActive()&&moveCodes.has(e.code)){e.preventDefault();moveKeys.add(e.code);if(!e.repeat)moveCamera(1/60);return;}if(e.code==='Space'){e.preventDefault();$('play').click();}if(e.key.toLowerCase()==='h')clean();if(e.key.toLowerCase()==='r'){exitMouse();$('hoverRotate').checked=!hoverEnabled();hoverHint();}};
function tick(now){requestAnimationFrame(tick);const dt=Math.min((now-last)/1000,1);last=now;if(playing&&scene&&!loading){if(contentMode==='history'){historyPlayback?.advance(dt*Number($('speed').value));syncHistory();warmHistory();}else{time=boundedTime(time+dt*Number($('speed').value),scene.duration);syncTime();if(time===scene.duration)setPlay(false);}}moveCamera(dt);if(controls.enabled&&!pointerLocked()&&!lookDrag)controls.update();camera.updateMatrixWorld(true);if(mapReady&&viewer&&!loading){viewer.update();viewer.render();}else if(mapReady&&!loading)renderer.render(threeScene,camera);frames++;if(now-fpsStart>1200){$('renderfps').textContent=(frames*1000/(now-fpsStart)).toFixed(0)+' FPS';stage.dataset.diagnostics=JSON.stringify({camera:camera.position.toArray(),forward:camera.getWorldDirection(new THREE.Vector3()).toArray(),cursor:cursor?.position.toArray(),inputCamera:historyFrame?cameraFromPose(historyFrame.estimated_c2w).position:null,mode:contentMode,historyState:historyPlayback?.state,ready:viewer?.splatRenderReady,instanceCount:viewer?.splatMesh?.geometry?.instanceCount,pointDrawCount:observations?.geometry.drawRange.count,contextLost:renderer.getContext().isContextLost(),memory:renderer.info.memory,draw:renderer.info.render});fpsStart=now;frames=0;}}
if(new URLSearchParams(location.search).get('mode')==='history'){contentMode='history';$('contentMode').value='history';}requestAnimationFrame(tick);const initialScene=new URLSearchParams(location.search).get('scene');if(initialScene){load(initialScene);}else if(new URLSearchParams(location.search).has('compare')){versionNumber='02';load('office');}else load('replica');






