import test from 'node:test';
import assert from 'node:assert/strict';
import {controlAvailability} from './ui-state.mjs';
test('no map and loading cannot expose pose-dependent actions',()=>{
 for(const loading of [false,true]){const a=controlAvailability({loading,ready:false,saved:true,mode:'gs'});assert.equal(a.map,false);assert.equal(a.restore,false);}
 assert.equal(controlAvailability({loading:true,ready:true,saved:true,mode:'gs'}).map,false);
});
test('failed load can retry scene and mode while restore stays unavailable',()=>{
 const a=controlAvailability({loading:false,ready:false,saved:false,mode:'gs'});assert.equal(a.mode,true);assert.equal(a.scene,true);assert.equal(a.restore,false);
});
test('observation mode locks its dataset but allows ready-map actions',()=>{
 const a=controlAvailability({loading:false,ready:true,saved:true,mode:'points'});assert.equal(a.scene,false);assert.equal(a.map,true);assert.equal(a.restore,true);
});
