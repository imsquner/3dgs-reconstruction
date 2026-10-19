import assert from 'node:assert/strict';
import {snapshotAtFrame,createLatestOnlyLoader} from './history-map.mjs';
const rows=[{source_frame:2,id:0},{source_frame:8,id:1},{source_frame:8,id:2}];
assert.equal(snapshotAtFrame(rows,0),null);assert.equal(snapshotAtFrame(rows,2).id,0);assert.equal(snapshotAtFrame(rows,7).id,0);assert.equal(snapshotAtFrame(rows,8).id,2);assert.equal(snapshotAtFrame(rows,100).id,2);
let resolve;const loaded=[],committed=[],disposed=[];const loader=createLatestOnlyLoader({load:async key=>{loaded.push(key);if(key===1)await new Promise(r=>resolve=r);return key;},commit:value=>committed.push(value),dispose:value=>disposed.push(value)});loader.request(1);loader.request(2);loader.request(3);resolve();await new Promise(r=>setTimeout(r,10));assert.deepEqual(loaded,[1,3]);assert.deepEqual(committed,[3]);assert.deepEqual(disposed,[1]);loader.stop();loader.request(4);await new Promise(r=>setTimeout(r,5));assert.deepEqual(loaded,[1,3]);console.log('history selection and latest-only lifecycle passed');
// A commit failure releases its payload exactly once and reports the active error.
{
 let released=0,errors=0;const x=createLatestOnlyLoader({load:async()=>({}),commit:async()=>{throw Error('GPU load failed');},dispose:async()=>{released++;}});x.request('broken',()=>errors++);await new Promise(r=>setTimeout(r,10));await x.stop();assert.equal(released,1);assert.equal(errors,1);
}
// Cancellation waits for an active commit to unwind before ownership can be reused.
{
 let finish,ended=false;const x=createLatestOnlyLoader({load:async()=>1,commit:async(v,k,current)=>{await new Promise(r=>finish=r);assert.equal(current(),false);ended=true;}});x.request(1);await new Promise(r=>setTimeout(r,1));const stopped=x.stop();assert.equal(ended,false);finish();await stopped;assert.equal(ended,true);
}
console.log('history failure disposal and cancellation checks passed');
