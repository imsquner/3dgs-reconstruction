import * as THREE from '../../vendor/three.module.js';
export function parseMedicalMesh(text){
 const end=text.indexOf('end_header');if(end<0)throw Error('Invalid PLY header');const lines=text.slice(0,end).split(/\r?\n/);if(!lines.includes('format ascii 1.0'))throw Error('Expected native ASCII mesh');
 const nv=Number(lines.find(x=>x.startsWith('element vertex ')).split(' ').at(-1)),nf=Number(lines.find(x=>x.startsWith('element face ')).split(' ').at(-1));const fields=[];let vertex=false;for(const l of lines){if(l.startsWith('element '))vertex=l.startsWith('element vertex ');else if(vertex&&l.startsWith('property '))fields.push(l.split(' ').at(-1));}
 const rows=text.slice(text.indexOf('\n',end)+1).trim().split(/\r?\n/);if(rows.length!==nv+nf)throw Error('Mesh row count mismatch');const xyz=new Float32Array(nv*3),rgb=new Float32Array(nv*3);const ri=fields.indexOf('red'),gi=fields.indexOf('green'),bi=fields.indexOf('blue');
 for(let i=0;i<nv;i++){const a=rows[i].trim().split(/\s+/).map(Number);xyz.set(a.slice(0,3),i*3);const c=new THREE.Color(ri>=0?a[ri]/255:.7,gi>=0?a[gi]/255:.7,bi>=0?a[bi]/255:.7);c.convertSRGBToLinear();rgb.set([c.r,c.g,c.b],i*3);}
 const idx=new Uint32Array(nf*3);for(let i=0;i<nf;i++){const a=rows[nv+i].trim().split(/\s+/).map(Number);if(a[0]!==3||a.slice(1).some(v=>v<0||v>=nv))throw Error('Invalid triangle');idx.set(a.slice(1,4),i*3);}
 if(!xyz.every(Number.isFinite))throw Error('Nonfinite mesh');const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(xyz,3));g.setAttribute('color',new THREE.BufferAttribute(rgb,3));g.setIndex(new THREE.BufferAttribute(idx,1));g.computeVertexNormals();g.computeBoundingBox();return new THREE.Mesh(g,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide}));
}
