import test from 'node:test';import assert from 'node:assert/strict';
import {officeVersions,resolveVersion} from './experiment-versions.mjs';
test('numbered versions preserve original and match requested assets',()=>{assert.deepEqual(officeVersions.map(v=>v.number),['00','01','02','03','04']);assert.equal(resolveVersion('office','02').assetKey,'office-exp-02');assert.equal(resolveVersion('office','04').assetKey,'office-exp-04');assert.equal(resolveVersion('office','00').assetKey,'office');});
test('comparison variants never inherit full-office observation accumulation',()=>{assert.equal(resolveVersion('office','02').observations,false);assert.equal(resolveVersion('office','04').observations,false);assert.equal(resolveVersion('office','00').observations,true);});
test('other sequences do not borrow experiment assets',()=>{assert.equal(resolveVersion('replica','04'),null);assert.throws(()=>resolveVersion('office','99'));});
