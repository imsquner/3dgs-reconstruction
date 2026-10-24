import assert from 'node:assert/strict';
import {loadHistoryMap} from './history-map.mjs';
const bytes=new Uint8Array([1,3,5,7]),originalFetch=globalThis.fetch,originalCrypto=globalThis.crypto;
const digest=await crypto.subtle.digest('SHA-256',bytes),sha256=Buffer.from(digest).toString('hex');
let requestedSignal;
globalThis.fetch=async(url,{signal})=>{requestedSignal=signal;return new Response(bytes);};
try{
 const controller=new AbortController(),row={ply:'/snapshots/test.ply',sha256};
 const value=await loadHistoryMap(row,{signal:controller.signal});
 assert.deepEqual(new Uint8Array(value.buffer),bytes);assert.equal(requestedSignal,controller.signal);
 await assert.rejects(loadHistoryMap({...row,sha256:'0'.repeat(64)}),/校验/);
 controller.abort();await assert.rejects(loadHistoryMap(row,{signal:controller.signal}),{name:'AbortError'});
 const hashing=new AbortController();let finishHash;
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:{subtle:{digest:()=>new Promise(resolve=>finishHash=()=>resolve(digest))}}});
 const pending=loadHistoryMap(row,{signal:hashing.signal});
 while(!finishHash)await new Promise(resolve=>setTimeout(resolve,0));
 hashing.abort();finishHash();await assert.rejects(pending,{name:'AbortError'});
 console.log('raw PLY bytes, real SHA match/mismatch, fetch signal and cancellation during SHA passed');
}finally{globalThis.fetch=originalFetch;Object.defineProperty(globalThis,'crypto',{configurable:true,value:originalCrypto});}
