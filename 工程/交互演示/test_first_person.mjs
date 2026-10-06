import test from 'node:test';
import assert from 'node:assert/strict';
import {lookDirection} from './first-person.mjs';
test('right movement turns right; downward movement looks down',()=>{
 assert.ok(lookDirection([0,0,-1],[0,1,0],100,0)[0]>0);
 assert.ok(lookDirection([0,0,-1],[0,1,0],0,100)[1]<0);
});
test('yaw completes full turns and pitch remains bounded',()=>{
 const f=lookDirection([0,0,-1],[0,1,0],2*Math.PI/.002,0);
 assert.ok(Math.hypot(f[0],f[1],f[2]+1)<1e-12);
 const p=lookDirection([0,0,-1],[0,1,0],0,-100000);
 assert.ok(p[1]<1&&p[1]>.99);assert.ok(Math.abs(Math.hypot(...p)-1)<1e-12);
});
