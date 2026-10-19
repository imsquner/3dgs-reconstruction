// Parse immutable native PLY and prepare bulk attributes off the UI thread.
const library=fetch('/vendor/gaussian-splats-3d.module.js').then(r=>r.text()).then(async source=>{
 const url=URL.createObjectURL(new Blob([source.replaceAll("from 'three'",`from '${location.origin}/vendor/three.module.js'`)],{type:'text/javascript'}));
 try{return await import(url);}finally{URL.revokeObjectURL(url);}
});
self.onmessage=async({data:{id,row}})=>{try{
 const started=performance.now(),{PlyParser}=await library;
 const response=await fetch(row.ply);if(!response.ok)throw Error(`地图 HTTP ${response.status}`);const raw=await response.arrayBuffer();
 const sha=[...new Uint8Array(await crypto.subtle.digest('SHA-256',raw))].map(v=>v.toString(16).padStart(2,'0')).join('');if(sha!==row.sha256)throw Error('快照校验失败');
 const readMs=performance.now()-started,buffer=PlyParser.parseToUncompressedSplatBuffer(raw,row.sh_degree),count=buffer.getSplatCount();
 if(count!==row.gaussians)throw Error('高斯数量不符');if(row.sh_degree!==0)throw Error('历史预处理仅适用于当前SH0快照');
 const centers=new Float32Array(count*3),covariances=new Float32Array(count*6),colors=new Uint8Array(count*4);
 buffer.fillSplatCenterArray(centers);buffer.fillSplatCovarianceArray(covariances,null,0,count-1,0,0);buffer.fillSplatColorArray(colors,0);
  const paddedCenters=new Float32Array(count*4),sceneIndexes=new Uint32Array(count);let radius=0;const center=buffer.sceneCenter.toArray();
 for(let i=0;i<count;i++){paddedCenters.set(centers.subarray(i*3,i*3+3),i*4);paddedCenters[i*4+3]=1;radius=Math.max(radius,Math.hypot(centers[i*3]-center[0],centers[i*3+1]-center[1],centers[i*3+2]-center[2]));}
 const result={id,buffer:buffer.bufferData,centers,covariances,colors,paddedCenters,sceneIndexes,center,radius,readMs,workerMs:performance.now()-started};
 self.postMessage(result,[result.buffer,centers.buffer,covariances.buffer,colors.buffer,paddedCenters.buffer,sceneIndexes.buffer]);
 }catch(e){self.postMessage({id,error:e.message});}};
