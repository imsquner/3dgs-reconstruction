import * as THREE from 'three';
import {Viewer,SceneRevealMode,LogLevel} from 'gs';
import {OrbitControls} from './vendor/OrbitControls.js';
import {cameraFromPose,sourceIndexAt,boundedTime} from './timeline.mjs';
import {controlAvailability} from './ui-state.mjs';
import {nativeLoadPromise} from './loader-bridge.mjs';
import {datasetsFor,datasetLabel,findSequence,selectCatalog,selectionCaption} from './catalog.mjs';
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
function hoverHint(){controls.enableRotate=false;controls.enableDamping=!pointerLocked();$('viewTip').textContent=pointerLocked()?'WASD 移动 · 空格上升 · Shift 下降 · 鼠标转向 · Esc 退出':hoverEnabled()?'点击地图进入 · WASD 移动 · 空格上升 · Shift 下降 · Esc 退出':'点击地图后 WASD 移动 · 空格上升 · Shift 下降 · 左键旋转';stage.dataset.pointerLocked=String(pointerLocked());}
function exitMouse(){if(pointerLocked())document.exitPointerLock();}
function lockFailure(error){$('hoverRotate').checked=false;hoverHint();stage.dataset.pointerLockError=error?.name||'pointerlockerror';$('viewTip').textContent='此浏览器未允许鼠标锁定，已恢复左键拖动。请在普通 Chrome / Edge 中开启鼠标进入模式再试。';}
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
renderer.domElement.addEventListener('pointerdown',e=>{if(e.button===0&&!hoverEnabled()&&mapReady&&!following)lookDrag={x:e.clientX,y:e.clientY};});
document.addEventListener('pointermove',e=>{if(!lookDrag||pointerLocked()||following||loading)return;if(!(e.buttons&1)){lookDrag=null;return;}turnView(e.clientX-lookDrag.x,e.clientY-lookDrag.y);lookDrag={x:e.clientX,y:e.clientY};});
document.addEventListener('pointerup',()=>{lookDrag=null;});
window.addEventListener('blur',()=>{lookDrag=null;});
$('hoverRotate').onchange=()=>{exitMouse();hoverHint();};
hoverHint();
const threeScene=new THREE.Scene();
let viewer,scene,line,cursor,observations,accumulation,contentMode='gs',playing=false,following=false,time=0,last=performance.now(),saved=null,token=0,loading=false,lastInput='';
let fpsStart=performance.now(),frames=0;
let mapReady=false,lastSceneId='replica',versionNumber='00';
function effectiveEntry(id=lastSceneId){return {...findSequence(id).sequence,...(resolveVersion(id,versionNumber)||{})};}
function versionUI(){const v=resolveVersion(lastSceneId,versionNumber);$('experimentPanel').hidden=!v;$('experimentVersion').replaceChildren(...officeVersions.map(x=>new Option(x.number+' · '+x.label,x.number)));$('experimentVersion').value=versionNumber;for(const n of ['02','04'])$('compare'+n).setAttribute('aria-pressed',String(versionNumber===n));}
async function chooseVersion(n){if(loading||lastSceneId!=='office'||n===versionNumber)return;const view={position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone(),time};versionNumber=n;contentMode='gs';$('contentMode').value='gs';await load('office',view);}
$('experimentVersion').onchange=e=>chooseVersion(e.target.value);$('compare02').onclick=()=>chooseVersion('02');$('compare04').onclick=()=>chooseVersion('04');
function lockControls(){const a=controlAvailability({loading,ready:mapReady,saved:!!saved,mode:contentMode});for(const id of ['category','dataset','scene','experimentVersion','compare02','compare04'])$(id).disabled=loading;$('contentMode').disabled=!a.mode;$('modeGs').disabled=!a.mode||!effectiveEntry().assetKey;$('modePoints').disabled=!a.mode||!effectiveEntry().observations;for(const id of ['free','follow','reset','overview','save','play','seek','trajectory'])$(id).disabled=!a.map;$('restore').disabled=!a.restore;controls.enabled=a.map&&!following;}
function catalogUI(id){const {dataset,sequence}=findSequence(id);$('category').value=dataset.category;$('dataset').replaceChildren(...datasetsFor(dataset.category).map(d=>new Option(datasetLabel(d),d.id)));$('dataset').value=dataset.id;$('dataset').title=datasetLabel(dataset);$('scene').replaceChildren(...dataset.sequences.map(s=>new Option(`${s.name} · ${s.status}`,s.id)));$('scene').value=sequence.id;$('scene').title=sequence.name;$('datasetSummary').textContent=`${datasetLabel(dataset)} / ${sequence.summary}`;$('sequenceState').textContent=sequence.status;$('sequenceState').dataset.available=String(!!sequence.assetKey);$('contentMode').querySelector('option[value="points"]').disabled=!effectiveEntry(id).observations;}
function chooseCatalog(selection){if(loading){catalogUI(lastSceneId);return;}const {sequence}=selectCatalog(selection);versionNumber='00';if(!sequence.observations){contentMode='gs';$('contentMode').value='gs';}load(sequence.id);}
function modeUI(){const entry=effectiveEntry();$('modeGs').setAttribute('aria-pressed',String(contentMode==='gs'));$('modePoints').setAttribute('aria-pressed',String(contentMode==='points'));$('modePoints').title=entry.observations?'切换到真实RGB-D观测累积':'本序列尚未提供观测累积资产';$('modeNote').textContent=!entry.assetKey?'本序列地图尚未接入，展示切换暂不可用。':contentMode==='points'?'点击播放或拖动时间轴，查看观测点随输入增加；这不是历史高斯快照。':entry.observations?'当前为固定的最终高斯地图。切换“观测累积”可查看输入逐步形成点云；沿轨迹模式可回放相机运动。':lastSceneId==='office'&&versionNumber!=='00'?'本组基于GS-ICP-SLAM的工程优化；当前为240帧最终地图，共用02相机回放。观测累积请切回00原始完整地图。':'本序列目前仅提供最终高斯地图，时间轴回放轨迹。';}
function status(text,progress=null,error=false){$('status').hidden=false;$('status').classList.remove('empty');$('statusLabel').textContent=text;$('status').classList.toggle('error',error);$('retry').hidden=!error;$('loadProgress').hidden=error;if(progress===null)$('loadProgress').removeAttribute('value');else $('loadProgress').value=progress;$('statusHint').textContent=error?(lastSceneId==='replica'?'缺少Replica地图时：在仓库运行 python tools/download_assets.py --package replica-research --accept-replica-terms（须先阅读研究条款）':'缺少地图时：在仓库运行 python tools/download_assets.py --website，再刷新页面'):'读取和整理本地模型，完成后即可移动视角';}
async function getAsset(path,type='json'){let r;try{r=await fetch(path);}catch(e){throw new Error(`本地服务连接中断（${path}）`);}if(!r.ok)throw new Error(`${path}（HTTP ${r.status}）`);return type==='json'?r.json():r.arrayBuffer();}
const trajectoryMaterial=new THREE.LineBasicMaterial({color:0x56dcc1,transparent:true,opacity:.8,depthTest:false});
function clock(t){return `${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;}
function resize(){
 const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;
 if(scene){const [W,H,fx,fy,cx,cy]=scene.intrinsic;camera.fov=2*Math.atan(H/(2*fy))*180/Math.PI;camera.updateProjectionMatrix();camera.projectionMatrix.elements[0]*=fx/fy;camera.projectionMatrix.elements[8]=-(2*cx+1-W)/H/camera.aspect;camera.projectionMatrix.elements[9]=(2*cy+1-H)/H;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();}
 else camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);
function setPose(p){const c=cameraFromPose(p);camera.position.fromArray(c.position);camera.up.fromArray(c.up);controls.target.fromArray(c.position).add(new THREE.Vector3().fromArray(c.forward).multiplyScalar(1.2));camera.lookAt(controls.target);controls.update();camera.updateMatrixWorld(true);}
function setFollow(value){if(value)exitMouse();following=value;if(!value&&scene){camera.up.fromArray(cameraFromPose(scene.poses[0]).up);camera.lookAt(controls.target);}$('follow').setAttribute('aria-pressed',String(value));$('free').setAttribute('aria-pressed',String(!value));controls.enabled=!value;$('follow').classList.toggle('active',value);$('free').classList.toggle('active',!value);$('stageLabel').textContent=selectionCaption(lastSceneId)+(lastSceneId==='office'?' · 版本'+versionNumber:'')+' · '+(contentMode==='points'?'观测累积':'最终3DGS')+' · '+(value?'轨迹回放':'自由视角');if(value)syncTime();}
function syncTime(){if(!scene)return;const i=sourceIndexAt(time,scene.input_fps,scene.indices);$('seek').value=time;$('elapsed').textContent=clock(time);$('frame').textContent=`源帧 ${scene.indices[i]} / ${scene.indices.at(-1)} · 轨迹位姿 ${i+1} / ${scene.poses.length}`;line?.geometry.setDrawRange(0,i+1);if(cursor)cursor.position.fromArray(cameraFromPose(scene.poses[i]).position);if(following)setPose(scene.poses[i]);if(contentMode==='points'&&accumulation&&observations){const k=sourceIndexAt(time,5,accumulation.chunks.map(c=>c.source_frame)),chunk=accumulation.chunks[k];observations.geometry.setDrawRange(0,chunk.point_count);$('count').textContent=chunk.point_count.toLocaleString()+' 观测点';if(lastInput!==chunk.input_image){$('inputImage').src=chunk.input_image;lastInput=chunk.input_image;}$('inputCaption').textContent=`实际RGB输入 · 源帧 ${chunk.source_frame} · 每5帧采样`;}}
function setPlay(value){playing=value;$('play').setAttribute('aria-pressed',String(value));buttonText('play',value?'暂停':'播放');$('play').querySelector('img').src=`vendor/icons/${value?'pause':'play'}.svg`;}
function overview(){if(!scene)return;setFollow(false);const box=observations?.geometry.boundingBox||(scene.map_bounds?new THREE.Box3(new THREE.Vector3(...scene.map_bounds[0]),new THREE.Vector3(...scene.map_bounds[1])):new THREE.Box3().setFromPoints(scene.poses.map(p=>new THREE.Vector3(...cameraFromPose(p).position)))),center=box.getCenter(new THREE.Vector3()),size=Math.max(box.getSize(new THREE.Vector3()).length(),.1);camera.position.copy(center).add(new THREE.Vector3(size*.53,-size*.53,size*.43));camera.up.copy(new THREE.Vector3(...cameraFromPose(scene.poses[0]).up));controls.target.copy(center);camera.lookAt(center);controls.update();camera.updateMatrixWorld(true);}
async function load(id,preserved=null){
 if(loading)return;exitMouse();const entry=effectiveEntry(id);catalogUI(id);loading=true;mapReady=false;lastSceneId=id;versionUI();delete stage.dataset.loadedVersion;delete stage.dataset.loadedScene;delete stage.dataset.loadedMode;const ticket=++token;setPlay(false);lockControls();modeUI();status('读取场景与轨迹');$('stageLabel').textContent=selectionCaption(id)+' · 地图未就绪';$('frame').textContent='源帧 —';$('elapsed').textContent='—';$('duration').textContent='—';$('boundary').textContent='地图未就绪，请等待加载或重试。';$('seek').max=1;$('seek').value=0;$('countLabel').textContent=contentMode==='points'?'累计观测点':'高斯数量';$('inputPreview').hidden=true;for(const field of ['kind','count','tracking','ate'])$(field).textContent='—';
 try{
  await clearMap();
  scene=null;time=0;setFollow(false);
  if(!entry.assetKey){status(entry.status);$('status').classList.add('empty');$('loadProgress').hidden=true;$('statusHint').textContent='该序列暂未提供可浏览地图，可选择其他序列。';$('stageLabel').textContent=selectionCaption(id)+' · '+entry.status;$('boundary').textContent=entry.summary+'；'+entry.status+'。各序列地图独立保存，当前没有加载其他序列的地图。';window.dispatchEvent(new Event('catalog-empty'));return;}
  scene=await getAsset(`assets/${entry.assetKey}.json`);if(ticket!==token)return;
  time=0;saved=null;$('restore').disabled=true;buttonText('save','保存当前视角');$('countLabel').textContent=contentMode==='points'?'累计观测点':'高斯数量';
  resize();setPose(scene.poses[0]);
  if(contentMode==='gs'){
   viewer=new Viewer({selfDrivenMode:false,renderer,camera,threeScene,useBuiltInControls:false,gpuAcceleratedSort:false,enableSIMDInSort:true,sharedMemoryForWorkers:crossOriginIsolated,integerBasedSort:false,halfPrecisionCovariancesOnGPU:false,sphericalHarmonicsDegree:0,sceneRevealMode:SceneRevealMode.Instant,logLevel:LogLevel.None,ignoreDevicePixelRatio:true});
   status('载入最终高斯地图');await nativeLoadPromise(viewer.addSplatScene(scene.ply,{splatAlphaRemovalThreshold:1,showLoadingUI:false,progressiveLoad:false,onProgress:p=>status('载入与整理高斯地图',Number.isFinite(p)?p:null)}));
  }else{
   status('读取 RGB-D 观测记录');accumulation=await getAsset('assets/office-accumulation.json');
   const [pb,cb]=await Promise.all([getAsset('assets/office-observations.xyz','binary'),getAsset('assets/office-observations.rgb','binary')]);
   const positions=new Float32Array(pb),bytes=new Uint8Array(cb),colors=new Float32Array(bytes.length);
   for(let i=0;i<bytes.length;i++){const v=bytes[i]/255;colors[i]=v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4);}
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(positions,3));geo.setAttribute('color',new THREE.BufferAttribute(colors,3));geo.computeBoundingSphere();geo.computeBoundingBox();
   observations=new THREE.Points(geo,new THREE.PointsMaterial({size:.013,vertexColors:true,sizeAttenuation:true}));threeScene.add(observations);
  }
  const pts=scene.poses.map(p=>new THREE.Vector3(...cameraFromPose(p).position));line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),trajectoryMaterial);line.renderOrder=20;threeScene.add(line);
  const scale=id==='unity'?.006:.018;cursor=new THREE.Mesh(new THREE.SphereGeometry(scale,10,8),new THREE.MeshBasicMaterial({color:0xffc766,depthTest:false}));cursor.renderOrder=21;threeScene.add(cursor);
  $('trackingLabel').textContent=scene.experiment?'建图总耗时折算（含优化）':'原实验跟踪吞吐';$('kind').textContent=scene.kind.split(' · ')[0];$('count').textContent=scene.gaussians.toLocaleString();$('tracking').textContent=scene.measured_tracking_fps.toFixed(2)+' FPS';$('ate').textContent=scene.ate_m===null||scene.ate_m===undefined?'未评价（尺度未确认）':(scene.ate_m*100).toFixed(2)+' cm';$('duration').textContent=clock(scene.duration);$('seek').max=scene.duration;$('boundary').textContent=contentMode==='points'?'真实RGB-D＋记录的估计位姿，顺序累积观测点。每5帧/每6像素采样，1.5cm体素保留首次观测；不是历史3DGS地图，也不是本轮在线性能测量。':scene.bounds;$('inputPreview').hidden=contentMode!=='points';
  setFollow(false);if(preserved){time=Math.min(preserved.time,scene.duration);camera.position.copy(preserved.position);camera.up.copy(preserved.up);controls.target.copy(preserved.target);controls.update();camera.updateMatrixWorld(true);}syncTime();line.visible=cursor.visible=$('trajectory').checked;mapReady=true;stage.dataset.loadedScene=id;stage.dataset.loadedVersion=versionNumber;stage.dataset.loadedMode=contentMode;const e=scene.experiment;$('experimentMetrics').textContent=e?`版本${versionNumber} · ${e.frames}帧 · ${e.steps_per_frame}步/帧\nPSNR ${e.metrics.psnr_db.toFixed(2)} dB · SSIM ${e.metrics.ssim.toFixed(4)}\n实验耗时 ${e.wall_seconds.toFixed(1)}秒`: '原始完整地图保留；不能与240帧短段作等范围量化对照。';$('status').hidden=true;window.dispatchEvent(new Event('scene-ready'));
 }catch(e){console.error(e);mapReady=false;await clearMap();scene=null;status('地图加载失败：'+e.message,null,true);}
 finally{loading=false;lockControls();}
}
async function clearMap(){
 const oldViewer=viewer;viewer=null;
 if(oldViewer){try{await oldViewer.dispose();}catch(e){console.warn('Viewer cleanup reported an error',e);}}
 if(observations){threeScene.remove(observations);observations.geometry.dispose();observations.material.dispose();observations=null;}
 if(line){threeScene.remove(line);line.geometry.dispose();line=null;}
 if(cursor){threeScene.remove(cursor);cursor.geometry.dispose();cursor.material.dispose();cursor=null;}
 accumulation=null;lastInput='';saved=null;
}
$('category').onchange=e=>chooseCatalog({category:e.target.value});$('dataset').onchange=e=>chooseCatalog({category:$('category').value,datasetId:e.target.value});$('scene').onchange=e=>chooseCatalog({category:$('category').value,datasetId:$('dataset').value,sequenceId:e.target.value});$('contentMode').onchange=e=>{if(loading){e.target.value=contentMode;return;}if(e.target.value==='points'&&!effectiveEntry().observations){e.target.value=contentMode;return;}contentMode=e.target.value;load(lastSceneId);};$('free').onclick=()=>setFollow(false);$('follow').onclick=()=>setFollow(true);
$('modeGs').onclick=()=>{if(loading||contentMode==='gs')return;$('contentMode').value='gs';$('contentMode').dispatchEvent(new Event('change'));};$('modePoints').onclick=()=>{if(loading||contentMode==='points')return;$('contentMode').value='points';$('contentMode').dispatchEvent(new Event('change'));};$('retry').onclick=()=>load(lastSceneId);
$('play').onclick=()=>{if(!scene||loading)return;if(time>=scene.duration)time=0;setPlay(!playing);};$('seek').oninput=e=>{time=Number(e.target.value);syncTime();};
$('reset').onclick=()=>{setPlay(false);time=0;setFollow(false);setPose(scene.poses[0]);syncTime();};$('overview').onclick=overview;
$('save').onclick=()=>{saved={position:camera.position.clone(),up:camera.up.clone(),target:controls.target.clone()};$('restore').disabled=false;buttonText('save','视角已保存');};
$('restore').onclick=()=>{if(!saved)return;setFollow(false);camera.position.copy(saved.position);camera.up.copy(saved.up);controls.target.copy(saved.target);controls.update();};
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
 const bounds=scene.map_bounds,extent=bounds?new THREE.Vector3(...bounds[1]).sub(new THREE.Vector3(...bounds[0])).length():camera.position.distanceTo(controls.target);
 movement.normalize().multiplyScalar(Math.max(extent*.15,.0001)*Math.min(dt,.05));camera.position.add(movement);controls.target.add(movement);
}
document.addEventListener('keyup',e=>moveKeys.delete(e.code));
window.addEventListener('blur',()=>moveKeys.clear());
document.addEventListener('visibilitychange',()=>{if(document.hidden)moveKeys.clear();});
document.onkeydown=e=>{if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(e.target.tagName)||e.target.isContentEditable)return;if(e.key==='Escape'){moveKeys.clear();exitMouse();renderer.domElement.blur();return;}if(navigationActive()&&moveCodes.has(e.code)){e.preventDefault();moveKeys.add(e.code);return;}if(e.code==='Space'){e.preventDefault();$('play').click();}if(e.key.toLowerCase()==='h')clean();if(e.key.toLowerCase()==='r'){exitMouse();$('hoverRotate').checked=!hoverEnabled();hoverHint();}};
function tick(now){requestAnimationFrame(tick);const dt=Math.min((now-last)/1000,1);last=now;if(playing&&scene&&!loading){time=boundedTime(time+dt*Number($('speed').value),scene.duration);syncTime();if(time===scene.duration)setPlay(false);}moveCamera(dt);if(controls.enabled&&!pointerLocked()&&!lookDrag)controls.update();camera.updateMatrixWorld(true);if(mapReady&&viewer&&!loading){viewer.update();viewer.render();}else if(mapReady&&!loading)renderer.render(threeScene,camera);frames++;if(now-fpsStart>1200){$('renderfps').textContent=(frames*1000/(now-fpsStart)).toFixed(0)+' FPS';stage.dataset.diagnostics=JSON.stringify({camera:camera.position.toArray(),forward:camera.getWorldDirection(new THREE.Vector3()).toArray(),mode:contentMode,ready:viewer?.splatRenderReady,instanceCount:viewer?.splatMesh?.geometry?.instanceCount,pointDrawCount:observations?.geometry.drawRange.count,contextLost:renderer.getContext().isContextLost(),memory:renderer.info.memory,draw:renderer.info.render});fpsStart=now;frames=0;}}
requestAnimationFrame(tick);if(new URLSearchParams(location.search).has('compare')){versionNumber='02';load('office');}else load('office');
