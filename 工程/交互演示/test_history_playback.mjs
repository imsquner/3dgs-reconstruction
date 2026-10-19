import assert from 'node:assert/strict';
import * as history from './history-map.mjs';
assert.equal(typeof history.createHistoryPlayback,'function','separate sequential playback is required');
const frames=[0,1,2,3].map(source_frame=>({source_frame}));
const snapshots=[{snapshot_id:0,source_frame:0},{snapshot_id:1,source_frame:2},{snapshot_id:2,source_frame:3},{snapshot_id:3,source_frame:3,final:true}];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
{
 const commits=[];
 const p=history.createHistoryPlayback({frames,snapshots,fps:1,load:async t=>{await sleep(4);return t;},commit:(v,t)=>commits.push([t.frameIndex,t.mapIndex])});
 await p.seek(0);
 p.advance(1);const frozen=p.state.time;
 for(let i=0;i<10;i++)p.advance(10);
 assert.equal(p.state.time,frozen,'clock must not outrun a pending transaction');
 await p.whenIdle();
 for(let i=0;i<12&&!p.state.done;i++){p.advance(10);await p.whenIdle();}
 assert.deepEqual(commits,[[0,0],[1,0],[2,1],[3,2],[3,3]],'every input and same-frame final map must commit');
 assert.equal(p.state.done,true);await p.stop();
}
{
 let release;const commits=[],disposed=[];
 const p=history.createHistoryPlayback({frames,snapshots,fps:1,load:async t=>{if(t.frameIndex===1)await new Promise(r=>release=r);return t;},commit:(v,t)=>commits.push(t.frameIndex),dispose:v=>disposed.push(v.frameIndex)});
 await p.seek(0);p.seek(1);await sleep(0);p.seek(2);p.seek(3);release();await p.whenIdle();
 assert.deepEqual(commits,[0,3]);assert.deepEqual(disposed,[1]);assert.equal(p.state.mapIndex,3);
 await p.stop();p.advance(10);assert.deepEqual(commits,[0,3]);
}
{
 let errors=0;const p=history.createHistoryPlayback({frames,snapshots,fps:1,load:async()=>{throw Error('decode');},commit:()=>assert.fail('failed data committed'),onError:()=>errors++});
 await p.seek(0);assert.equal(errors,1);assert.equal(p.state.failed,true);assert.equal(p.state.frameIndex,-1);await p.stop();
}
console.log('sequential playback, backpressure, all inputs, duplicate-frame final, seek cancellation and errors passed');
{
 let errors=0;const p=history.createHistoryPlayback({frames,snapshots,fps:1,load:async()=>({}),commit:()=>{throw Error('commit');},dispose:async()=>{throw Error('cleanup');},onError:()=>errors++});
 await p.seek(0);assert.equal(p.state.failed,true,'cleanup rejection must not bypass playback error state');assert.equal(errors,1);await p.stop();
}
