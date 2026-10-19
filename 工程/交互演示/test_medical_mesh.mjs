import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseMedicalMesh} from './assets/medical/mesh-loader.mjs';
test('native medical meshes retain vertices, triangles, color and double-side visibility',()=>{
 for(const ds of ['trans_t2_b','cecum_t1_a']){
  const base=new URL(`./assets/medical/tsdf/${ds}/open3d_point_to_plane_v0500/`,import.meta.url);
  const scene=JSON.parse(readFileSync(new URL('scene.json',base),'utf8'));
  const m=parseMedicalMesh(readFileSync(new URL('mesh_m.ply',base),'utf8'));
  assert.equal(m.geometry.getAttribute('position').count,scene.vertices);
  assert.equal(m.geometry.index.count,scene.triangles*3);
  assert.equal(m.geometry.getAttribute('color').count,scene.vertices);
  assert.equal(m.material.side,2);m.geometry.dispose();m.material.dispose();
 }
});
test('malformed mesh cannot silently display the prior model',()=>{
 assert.throws(()=>parseMedicalMesh('invalid'),/Invalid PLY/);
});
