import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {sourceIndexAt} from './timeline.mjs';
for(const [run,m,start,end,count] of [['smoke30-a2',0,0,29,94011],['stress150-a2',0,0,49,150564],['stress150-a2',1,50,99,58216],['stress150-a2',2,100,148,70329],['stress150-a2',3,149,149,72120]]){
 test(`LoopSplat ${run}/sm${m} has isolated, verified frame and map assets`,()=>{
  const root=`assets/natural/loopsplat/${run}/sm${m}/`,s=JSON.parse(fs.readFileSync(root+'scene.json')),p=JSON.parse(fs.readFileSync(root+'asset-verification.json')),a=JSON.parse(fs.readFileSync(root+'accumulation.json'));
  assert.deepEqual(s.indices,Array.from({length:end-start+1},(_,i)=>start+i));assert.equal(s.poses.length,s.indices.length);assert.equal(s.gaussians,count);assert.equal(s.gaussian_quaternion_order,'wxyz');assert.equal(p.independent_submap,true);assert.equal(p.not_merged,true);
  for(const [file,hash] of Object.entries(p.files))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(root+file)).digest('hex'),hash);
  assert.equal(new Set(s.fixed_views.map(v=>JSON.stringify(v.position))).size,9);
  for(const v of s.fixed_views)assert.ok([...v.position,...v.look_at,...v.up].every(Number.isFinite));
  assert.equal(s.duration,s.frame_times.at(-1));assert.equal(sourceIndexAt(s.duration-1e-12,30,s.indices,s.frame_times),s.indices.length-1);
  let sum=0;for(const [i,c] of a.chunks.entries()){sum+=c.added;assert.equal(c.point_count,sum);assert.equal(c.source_frame,s.indices[i]);assert.equal(c.input_image,s.rgb_images[i]);assert.ok(fs.existsSync(c.input_image));}
  assert.equal(sum,a.points);assert.equal(fs.statSync(root+'observations.xyz').size,sum*12);assert.equal(fs.statSync(root+'observations.rgb').size,sum*3);
 });
}
