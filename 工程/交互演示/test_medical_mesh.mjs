import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseMedicalMesh} from './assets/medical/mesh-loader.mjs';

const PLY = `ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
element face 1
property list uchar int vertex_indices
end_header
0 0 0 255 0 0
1 0 0 0 255 0
0 1 0 0 0 255
3 0 1 2
`;

test('medical mesh parser keeps vertices, triangles and per-vertex colour', () => {
  const mesh = parseMedicalMesh(PLY);
  assert.equal(mesh.geometry.getAttribute('position').count, 3);
  assert.equal(mesh.geometry.index.count, 3);
  assert.equal(mesh.geometry.getAttribute('color').count, 3);
  assert.equal(mesh.material.side, 2);
  mesh.geometry.dispose();
  mesh.material.dispose();
});

test('the two published demo scenes declare a valid mesh manifest', () => {
  for (const ds of ['trans_t2_b', 'cecum_t1_a']) {
    const rel = ds === 'trans_t2_b' ? 'trans_t2_b/open3d_park_v0500' : 'cecum_t1_a/open3d_park_v1000';
    const scene = JSON.parse(readFileSync(new URL(`./assets/medical/tsdf/${rel}/scene.json`, import.meta.url), 'utf8'));
    assert.ok(scene.vertices > 0, `${ds} vertices`);
    assert.ok(scene.triangles > 0, `${ds} triangles`);
    assert.match(scene.ply, /medical\/tsdf\//);
    assert.equal(scene.intrinsic.length, 6);
  }
});

test('malformed mesh cannot silently display the prior model', () => {
  assert.throws(() => parseMedicalMesh('invalid'), /Invalid PLY/);
});
