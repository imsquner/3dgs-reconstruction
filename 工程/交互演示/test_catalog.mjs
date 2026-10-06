import test from 'node:test';
import assert from 'node:assert/strict';
import {catalog,findSequence,selectCatalog,datasetsFor,selectionCaption} from './catalog.mjs';
test('catalog has unique stable dataset and sequence identifiers',()=>{
 assert.equal(new Set(catalog.map(d=>d.id)).size,4);
 const ids=catalog.flatMap(d=>d.sequences.map(s=>s.id));
 assert.equal(ids.length,8);assert.equal(new Set(ids).size,8);
 assert.deepEqual(catalog.map(d=>d.number),['01','02','03','04']);
});
test('category and dataset transitions prefer available maps without crossing categories',()=>{
 assert.equal(selectCatalog({category:'medical'}).sequence.id,'unity');
 assert.equal(selectCatalog({category:'natural',datasetId:'tum'}).sequence.id,'office');
 assert.equal(selectCatalog({category:'medical',datasetId:'replica'}).dataset.id,'endoslam');
 assert.equal(datasetsFor('natural').length,2);
});
test('unavailable sequence remains selectable and does not borrow another asset',()=>{
 const c=selectCatalog({category:'medical',datasetId:'c3vd',sequenceId:'c3vd-trans-t2-b'});
 assert.equal(c.sequence.assetKey,null);assert.equal(c.sequence.status,'开发结果，尚未接入');
 assert.equal(findSequence('desk').sequence.assetKey,null);
 assert.equal(findSequence('office').sequence.observations,true);
 assert.equal(findSequence('unity').sequence.observations,false);
});
test('caption preserves original sequence name and unknown ids fail explicitly',()=>{
 assert.match(selectionCaption('office'),/rgbd_dataset_freiburg3_long_office_household/);
 assert.throws(()=>findSequence('invented'),/Unknown sequence/);
});
