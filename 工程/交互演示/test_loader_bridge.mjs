import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeLoadPromise} from './loader-bridge.mjs';
test('loader wrapper rejection reaches await instead of hanging its incomplete thenable',async()=>{
 const wrapper={promise:Promise.reject(new Error('PLY fetch failed')),then(onResolve){return this.promise.then(onResolve);}};
 await assert.rejects(nativeLoadPromise(wrapper),/PLY fetch failed/);
});
test('standard loader promises keep their success value',async()=>{
 const request=Promise.resolve('ready');assert.equal(nativeLoadPromise(request),request);
 assert.equal(await nativeLoadPromise(request),'ready');
});
