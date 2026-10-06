import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraFromPose, sourceIndexAt, boundedTime} from './timeline.mjs';
test('CV identity camera points toward +Z and uses negative Y up',()=>{
 const p=[[1,0,0,2],[0,1,0,3],[0,0,1,4],[0,0,0,1]];
 assert.deepEqual(cameraFromPose(p),{position:[2,3,4],forward:[0,0,1],up:[0,-1,0]});
});
test('rotated pose preserves forward axis and translation',()=>{
 const p=[[0,0,1,5],[0,1,0,6],[-1,0,0,7],[0,0,0,1]];
 assert.deepEqual(cameraFromPose(p).forward,[1,0,0]);
 assert.deepEqual(cameraFromPose(p).position,[5,6,7]);
});
test('timeline uses actual source indices across held-out gaps',()=>{
 const indices=[0,1,3,4];
 assert.equal(sourceIndexAt(0,5,indices),0);
 assert.equal(sourceIndexAt(.4,5,indices),1);
 assert.equal(sourceIndexAt(.6,5,indices),2);
 assert.equal(sourceIndexAt(100,5,indices),3);
 assert.equal(boundedTime(-1,2),0);
 assert.equal(boundedTime(9,2),2);
});
