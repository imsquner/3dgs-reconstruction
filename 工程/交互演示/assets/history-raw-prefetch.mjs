// Only verified raw bytes are retained. No parsing, Viewer or GPU work here.
export function createRawPrefetch(load){
 let entry=null;
 let tail=Promise.resolve();const readers=new Set();
 const stats={started:0,used:0,miss:0,fallback:0,cleared:0};
 const key=row=>`${row.ply}|${row.sha256}`;
 const aborted=()=>new DOMException('Raw prefetch aborted','AbortError');
 function start(row,controller){
  readers.add(controller);
  const promise=tail.then(async()=>{
   if(controller.signal.aborted)throw aborted();
   const value=await load(row,{signal:controller.signal});
   if(controller.signal.aborted)throw aborted();
   return {value};
  }).catch(error=>({error})).finally(()=>readers.delete(controller));
  tail=promise.then(()=>{});return promise;
 }
 function clear(){const old=entry;entry=null;if(old)stats.cleared++;for(const controller of readers)controller.abort();}
 function warm(row){
  if(!row||entry?.key===key(row))return;
  clear();const controller=new AbortController(),item={key:key(row),controller};
  entry=item;
  stats.started++;
  item.promise=start(row,controller);
 }
 return {warm,clear,get stats(){return {...stats};},async take(row){
  const item=entry;
  if(item?.key===key(row)){
   entry=null;const result=await item.promise;
   if(!result.error){stats.used++;return result.value;}
   if(item.controller.signal.aborted)throw result.error;
   stats.fallback++;
  }else{stats.miss++;clear();}
  const result=await start(row,new AbortController());if(result.error)throw result.error;return result.value;
 }};
}
