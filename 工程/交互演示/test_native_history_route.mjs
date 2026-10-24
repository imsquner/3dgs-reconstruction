import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('./app.mjs',import.meta.url),'utf8');
const body=source.slice(source.indexOf('async function buildHistoryMap(row,isCurrent){'),source.indexOf('async function prepareHistory(target,isCurrent){'));
assert.ok(body.startsWith('async function buildHistoryMap'));
assert.doesNotMatch(source,/new Worker|addSplatBuffers|compactDataTextures|uploadHistoryTexture|historyMapSlot/);
let calls=[],revoked=[],disposed=0,fail=false;
class FakeViewer{
 constructor(options){calls.push({kind:'viewer',options});this.splatRenderReady=true;}
 addSplatScene(url,options){calls.push({kind:'native-load',url,options});if(fail)throw Error('native load failed');return Promise.resolve();}
}
const deps={historyRetiring:Promise.resolve(),loadHistoryMap:async row=>{calls.push({kind:'raw-ply',row});return {buffer:new ArrayBuffer(32)};},Viewer:FakeViewer,renderer:{},camera:{},threeScene:{},crossOriginIsolated:false,SceneRevealMode:{Instant:1},LogLevel:{None:0},URL:{createObjectURL:()=> 'blob:native-test',revokeObjectURL:url=>revoked.push(url)},Blob,performance,window:{},nativeLoadPromise:p=>p,disposePreparedViewer:async()=>{disposed++;}};
deps.rawPrefetch=null;
const make=new Function('deps',`const {${Object.keys(deps).join(',')}}=deps;${body};return buildHistoryMap;`),load=make(deps),row={snapshot_id:7,sh_degree:0};
const result=await load(row,()=>true);
assert.ok(result.candidate instanceof FakeViewer);assert.equal(calls[0].kind,'raw-ply');
assert.equal(calls[1].options.optimizeSplatData,true);assert.equal(calls[1].options.halfPrecisionCovariancesOnGPU,false);
assert.equal(calls[2].kind,'native-load');assert.deepEqual(calls[2].options,{format:2,splatAlphaRemovalThreshold:0,showLoadingUI:false,progressiveLoad:false});
assert.deepEqual(revoked,['blob:native-test']);assert.equal(deps.window.historyPerf[0].pipeline,'native-ply');
calls=[];assert.equal(await load(row,()=>false),null);assert.equal(calls.length,0);
fail=true;await assert.rejects(load(row,()=>true),/native load failed/);assert.equal(disposed,1);assert.equal(revoked.length,2);
fail=false;calls=[];let takes=0;
deps.rawPrefetch={take:async()=>{takes++;return {buffer:new ArrayBuffer(32)};}};
const hybrid=make(deps);await hybrid(row,()=>true);
assert.equal(takes,1);assert.equal(calls[0].kind,'viewer');assert.equal(calls[0].options.optimizeSplatData,true);assert.equal(calls[1].kind,'native-load');
console.log('native PLY Viewer route restored, optimize enabled, no worker/cache/direct-buffer/compact/upload route; failure cleanup passed');
