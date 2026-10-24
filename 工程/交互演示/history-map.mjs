export function snapshotAtFrame(rows,frame){let found=null;for(const row of rows){if(row.source_frame>frame)break;found=row;}return found;}
// One active load and one replaceable target; superseded CPU payloads are released.
export function createLatestOnlyLoader({load,commit,dispose=()=>{}}){let serial=0,pending=null,running=false,stopped=false,idle=[];async function pump(){if(running)return;running=true;try{while(pending&&!stopped){const task=pending;pending=null;let value,owned=false;try{value=await load(task.key);owned=true;if(stopped||task.id!==serial){owned=false;await dispose(value);continue;}await commit(value,task.key,()=>!stopped&&task.id===serial);}catch(error){if(owned){owned=false;try{await dispose(value);}catch{}}if(task.id===serial&&!stopped)task.error?.(error);}}}finally{running=false;for(const resolve of idle.splice(0))resolve();}}return {request(key,error){if(stopped)return;pending={key,error,id:++serial};void pump();},cancel(){serial++;pending=null;},stop(){stopped=true;serial++;pending=null;return running?new Promise(resolve=>idle.push(resolve)):Promise.resolve();}};}
export async function loadHistoryPayload(row){const response=await fetch(row.ply);if(!response.ok)throw Error(`地图 HTTP ${response.status}`);const buffer=await response.arrayBuffer();const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(x=>x.toString(16).padStart(2,'0')).join('');if(actual!==row.sha256)throw Error('快照校验失败');const images=await Promise.all([row.rgb,row.depth].map(src=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('输入图像读取失败'));image.src=src;})));return {row,buffer,images};}

// Auto playback has backpressure; only an explicit seek supersedes a transaction.
// Commit is synchronous so a user seek cannot interleave half of a presentation.
export function createHistoryPlayback({frames,snapshots,fps,load,commit,dispose=()=>{},onState=()=>{},onError=()=>{}}){
 if(!frames?.length||!snapshots?.length||!(fps>0))throw Error('Missing history inputs/maps');
 let frameIndex=-1,mapIndex=-1,time=0,serial=0,pending=null,running=false,stopped=false,failed=false,idle=[];
 const end=frames.at(-1).source_frame/fps;
 const state=()=>({frameIndex,mapIndex,time,busy:running||!!pending,failed,done:frameIndex===frames.length-1&&mapIndex===snapshots.length-1&&!running&&!pending,requested:pending?.frameIndex??null});
 const emit=()=>onState(state());
 async function pump(){
  if(running)return;running=true;emit();
  try{while(pending&&!stopped){
   const job=pending;pending=null;let payload,owned=false;
   const current=()=>!stopped&&job.serial===serial;
   const target={...job,input:frames[job.frameIndex],map:snapshots[job.mapIndex],mapChanged:job.mapIndex!==mapIndex,inputChanged:job.frameIndex!==frameIndex};
   try{
    payload=await load(target,current);owned=true;
    if(!current()){owned=false;await dispose(payload);continue;}
    const result=commit(payload,target);if(result?.then)throw Error('History commit must be synchronous');
    owned=false;frameIndex=job.frameIndex;mapIndex=job.mapIndex;time=job.time;failed=false;emit();
   }catch(error){let failure=error;if(owned){try{await dispose(payload);}catch(cleanup){failure=new AggregateError([error,cleanup],'历史提交及资源清理失败');}}if(current()){failed=true;pending=null;onError(failure);emit();}}
  }}finally{running=false;emit();for(const resolve of idle.splice(0))resolve();}
 }
 function request(target){if(stopped)return;failed=false;pending={...target,serial:++serial};void pump();}
 const whenIdle=()=>running||pending?new Promise(resolve=>idle.push(resolve)):Promise.resolve();
 return {
  get state(){return state();},whenIdle,
  seek(seconds){
   if(stopped)return Promise.resolve();const targetTime=Math.max(0,Math.min(end,Number(seconds)||0));
   let fi=0,mi=0;while(fi+1<frames.length&&frames[fi+1].source_frame/fps<=targetTime+1e-8)fi++;
   while(mi+1<snapshots.length&&snapshots[mi+1].source_frame<=frames[fi].source_frame)mi++;
   request({frameIndex:fi,mapIndex:mi,time:targetTime,mode:'seek'});return whenIdle();
  },
  advance(dt){
   if(stopped||failed||running||pending||frameIndex<0)return;
   if(mapIndex+1<snapshots.length&&snapshots[mapIndex+1].source_frame<=frames[frameIndex].source_frame){request({frameIndex,mapIndex:mapIndex+1,time,mode:'auto'});return;}
   if(frameIndex+1>=frames.length)return;
   const next=frameIndex+1,boundary=frames[next].source_frame/fps;
   const proposed=Math.min(end,time+Math.max(0,dt));
   if(proposed+1e-8>=boundary){const mi=mapIndex+1<snapshots.length&&snapshots[mapIndex+1].source_frame<=frames[next].source_frame?mapIndex+1:mapIndex;request({frameIndex:next,mapIndex:mi,time:boundary,mode:'auto'});}
   else{time=proposed;emit();}
  },
  async stop(){stopped=true;serial++;pending=null;await whenIdle();}
 };
}

export async function loadHistoryInput(row){
 const images=await Promise.all([row.rgb,row.depth].map(src=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('输入图像读取失败'));image.src=src;})));
 return {row,images};
}
export async function loadHistoryMap(row,{signal}={}){
 const response=await fetch(row.ply,{signal});if(!response.ok)throw Error(`地图 HTTP ${response.status}`);
 signal?.throwIfAborted();
 const buffer=await response.arrayBuffer();const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(x=>x.toString(16).padStart(2,'0')).join('');
 signal?.throwIfAborted();
 if(hash!==row.sha256)throw Error('快照校验失败');return {row,buffer};
}

// One prepared map only; replacement waits for stale work and releases its GPU owner.
export function createPreparedHistorySlot({load,dispose}){
 let entry=null,tail=Promise.resolve(),stopped=false;
 async function release(item){if(item?.value&&!item.taken){const value=item.value;item.value=null;await dispose(value);}}
 function warm(key){
  if(stopped)return null;
  if(entry?.key===key)return entry;
  const old=entry;if(old)old.valid=false;
  const item=entry={key,valid:true,taken:false,value:null};
  item.promise=tail.then(async()=>{await release(old);if(!item.valid)return null;const value=await load(key,()=>item.valid&&!stopped);item.value=value;if(!item.valid||stopped){await release(item);return null;}return value;});
  tail=item.promise.catch(()=>{});return item;
 }
 return {
  warm(key){const item=warm(key);item?.promise.catch(()=>{});},
  async take(key){const item=warm(key);if(!item)return null;const value=await item.promise;if(entry!==item||!item.valid)return null;item.taken=true;entry=null;return value;},
  async clear(){const old=entry;entry=null;if(old)old.valid=false;await tail;await release(old);},
  async stop(){stopped=true;const old=entry;entry=null;if(old)old.valid=false;await tail;await release(old);}
 };
}

export async function disposePreparedViewer(viewer){
 if(!viewer)return;
 const mesh=viewer.splatMesh,texture=mesh?.material?.uniforms?.covariancesTextureHalfFloat?.value;
 const orphan=texture?.isTexture&&!Object.values(mesh.splatDataTextures||{}).some(item=>item.texture===texture)?texture:null;
 try{await viewer.dispose();}finally{orphan?.dispose();}
}

export function installPreparedHistoryArrays(buffer,prepared){
 const count=buffer.getSplatCount(),identity=m=>!m||m.elements.every((v,i)=>v===(i%5===0?1:0));
 function copy(out,source,width,from=0,to=count-1,dest=from){out.set(source.subarray(from*width,(to+1)*width),dest*width);}
 const centers=buffer.fillSplatCenterArray.bind(buffer),cov=buffer.fillSplatCovarianceArray.bind(buffer),color=buffer.fillSplatColorArray.bind(buffer);
 buffer.fillSplatCenterArray=(out,transform,from,to,dest)=>prepared.centers&&identity(transform)?copy(out,prepared.centers,3,from,to,dest):centers(out,transform,from,to,dest);
 buffer.fillSplatCovarianceArray=(out,transform,from,to,dest,compression)=>prepared.covariances&&identity(transform)&&!compression?copy(out,prepared.covariances,6,from,to,dest):cov(out,transform,from,to,dest,compression);
 buffer.fillSplatColorArray=(out,alpha,from,to,dest)=>prepared.colors&&(!alpha||alpha===1)?copy(out,prepared.colors,4,from,to,dest):color(out,alpha,from,to,dest);
 return buffer;
}

export async function loadPreparedHistoryPresentation(inputPromise,mapPromise,dispose){
 const [input,map]=await Promise.allSettled([inputPromise,mapPromise]);
 if(input.status==='rejected'||map.status==='rejected'){
  if(map.status==='fulfilled')await dispose(map.value);
  throw input.status==='rejected'?input.reason:map.reason;
 }
 return {input:input.value,...map.value};
}

// Upload only addressed rows; WebGL storage is allocated normally by Three.
// Interception lasts only for synchronous initTexture; rendering keeps native GL.
export async function uploadHistoryTexture(renderer,texture,{rows=64,activeRows=Infinity,yieldFrame=()=>new Promise(requestAnimationFrame)}={}){
 const gl=renderer.getContext(),native=gl.texSubImage2D,jobs=[];
 const unpack=[gl.UNPACK_ALIGNMENT,gl.UNPACK_ROW_LENGTH,gl.UNPACK_SKIP_PIXELS,gl.UNPACK_SKIP_ROWS,gl.UNPACK_IMAGE_HEIGHT,gl.UNPACK_SKIP_IMAGES,gl.UNPACK_FLIP_Y_WEBGL,gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,gl.UNPACK_COLORSPACE_CONVERSION_WEBGL];
 const components=new Map([[gl.RGBA,4],[gl.RGBA_INTEGER,4],[gl.RGB,3],[gl.RGB_INTEGER,3],[gl.RG,2],[gl.RG_INTEGER,2],[gl.RED,1],[gl.RED_INTEGER,1]]);
 gl.texSubImage2D=function(...args){
  const [target,level,x,y,width,height,format,type,pixels]=args,stride=width*components.get(format);
  const store=unpack.map(key=>[key,gl.getParameter(key)]);
  if(args.length!==9||target!==gl.TEXTURE_2D||!ArrayBuffer.isView(pixels)||!stride||texture.generateMipmaps||store.slice(1,6).some(([,value])=>value!==0))return native.apply(gl,args);
  jobs.push({args,stride,height:Math.min(height,Math.ceil(activeRows)),binding:gl.getParameter(gl.TEXTURE_BINDING_2D),store});
 };
 try{renderer.initTexture(texture);}finally{gl.texSubImage2D=native;}
 let bytes=0;
 for(const job of jobs){for(let from=0;from<job.height;from+=rows){
  await yieldFrame();const count=Math.min(rows,job.height-from),args=job.args.slice(),active=gl.getParameter(gl.ACTIVE_TEXTURE),oldStore=unpack.map(key=>[key,gl.getParameter(key)]);
  gl.activeTexture(gl.TEXTURE0);const oldTexture=gl.getParameter(gl.TEXTURE_BINDING_2D);
  try{gl.bindTexture(gl.TEXTURE_2D,job.binding);for(const [key,value]of job.store)gl.pixelStorei(key,value);args[3]+=from;args[5]=count;args[8]=args[8].subarray(from*job.stride,(from+count)*job.stride);native.apply(gl,args);bytes+=args[8].byteLength;}
  finally{for(const [key,value]of oldStore)gl.pixelStorei(key,value);gl.bindTexture(gl.TEXTURE_2D,oldTexture);gl.activeTexture(active);}
 }}
 return bytes;
}
