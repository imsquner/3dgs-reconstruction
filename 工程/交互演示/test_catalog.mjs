import test from 'node:test';
import assert from 'node:assert/strict';
import {catalog,findSequence,selectCatalog,datasetsFor,selectionCaption,sequenceGroups} from './catalog.mjs';

test('demo catalog keeps four datasets and five sequences',()=>{
 assert.equal(catalog.length,4);
 assert.deepEqual(catalog.map(d=>d.number),['01','02','03','04']);
 const ids=catalog.flatMap(d=>d.sequences.map(s=>s.id));
 assert.equal(ids.length,5);assert.equal(new Set(ids).size,5);
});

test('category transitions stay inside the selected category',()=>{
 assert.equal(selectCatalog({category:'medical'}).sequence.id,'medmesh-trans_t2_b-open3d_park_v0500');
 assert.equal(selectCatalog({category:'natural'}).sequence.id,'replica');
 assert.equal(datasetsFor('natural').length,3);
 assert.equal(selectCatalog({category:'medical',datasetId:'replica'}).dataset.id,'medical-tsdf');
});

test('medical demo exposes exactly the two C3VD meshes',()=>{
 const d=findSequence('medmesh-trans_t2_b-open3d_park_v0500').dataset;
 assert.equal(d.id,'medical-tsdf');assert.equal(d.sequences.length,2);
 assert.equal(findSequence('medmesh-trans_t2_b-open3d_park_v0500').sequence.assetKey,'medical/tsdf/trans_t2_b/open3d_park_v0500/scene');
 assert.equal(findSequence('medmesh-cecum_t1_a-open3d_park_v1000').sequence.assetKey,'medical/tsdf/cecum_t1_a/open3d_park_v1000/scene');
 for(const s of d.sequences)assert.equal(s.observations,false,'observation buffers are not published in this build');
});

test('captions keep the showcase numbering',()=>{
 assert.match(selectionCaption('replica'),/汇报①/);
 assert.match(selectionCaption('tum-full-gsicp10'),/汇报②/);
 assert.match(selectionCaption('ooosplat-office-balanced'),/汇报③/);
 assert.match(selectionCaption('medmesh-trans_t2_b-open3d_park_v0500'),/演示①/);
 assert.match(selectionCaption('medmesh-cecum_t1_a-open3d_park_v1000'),/演示②/);
 assert.throws(()=>findSequence('invented'),/Unknown sequence/);
});

test('every dataset has a single ungrouped section',()=>{
 for(const d of catalog)assert.deepEqual(sequenceGroups(d.sequences).map(g=>g.label),[null]);
});
