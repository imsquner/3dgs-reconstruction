// Stable identifiers are independent of Chinese labels and asset filenames.
// Demo-only catalog: 3 natural scenes + 2 medical C3VD meshes.
// Observation-accumulation buffers are intentionally not published; the
// corresponding buttons stay disabled in this repository build.
const seq=(id,name,summary,status,assetKey=null,observations=false)=>({id,name,summary,status,assetKey,observations});
export const catalog=[
 {id:'replica',number:'01',category:'natural',name:'Replica',summary:'合成办公室',sequences:[
  seq('replica','office0','1801帧 · 在线 GS-ICP','已接入演示','replica')]},
 {id:'tum-comparison',number:'02',category:'natural',name:'TUM 实验对比',summary:'真实办公室在线重建',sequences:[
  seq('tum-full-gsicp10','office完整 / 在线 GS-ICP 10FPS','2515帧 · 真实在线跟踪 · 无回环／无全局BA','在线最佳结果；画面质量待验收','natural/tum-comparison/GSICP10')]},
 {id:'ooosplat',number:'03',category:'natural',name:'OOOSplat · RGB 离线重建',summary:'全量办公室 · 离线 SfM + 3DGS',sequences:[
  seq('ooosplat-office-balanced','办公室 / 均衡 15000 步','2585张RGB · COLMAP相机 · 尺度未标定','训练完成；展示质量待验收','natural/ooosplat-office/balanced/scene')]},
 {id:'medical-tsdf',number:'04',category:'medical',name:'医学 · C3VD 几何融合',summary:'两个序列 · ICP＋TSDF 三角网格',sequences:[
  seq('medmesh-trans_t2_b-open3d_park_v0500','trans_t2_b / open3d_park_v0500','103帧 · 演示①','已接入 · 开放网格','medical/tsdf/trans_t2_b/open3d_park_v0500/scene'),
  seq('medmesh-cecum_t1_a-open3d_park_v1000','cecum_t1_a / open3d_park_v1000','276帧 · 演示②','已接入 · 开放网格','medical/tsdf/cecum_t1_a/open3d_park_v1000/scene')]}
];
export function datasetsFor(category){return catalog.filter(d=>d.category===category);}
export function datasetLabel(d){return `${d.number} · ${d.name}`;}
export function sequenceGroups(sequences){
 const groups=new Map();
 for(const sequence of sequences){
  const label=typeof sequence.experimentGroup==='string'&&sequence.experimentGroup.trim()?sequence.experimentGroup:null;
  const key=label??'\u0000ungrouped';
  if(!groups.has(key))groups.set(key,{label,sequences:[]});
  groups.get(key).sequences.push(sequence);
 }
 return [...groups.values()];
}
export function findSequence(id){
 for(const dataset of catalog){const sequence=dataset.sequences.find(s=>s.id===id);if(sequence)return {dataset,sequence};}
 throw new Error(`Unknown sequence: ${id}`);
}
export function selectCatalog({category='natural',datasetId,sequenceId}={}){
 const available=datasetsFor(category);
 if(!available.length)throw new Error(`Unknown category: ${category}`);
 const dataset=available.find(d=>d.id===datasetId)||available[0];
 const sequence=dataset.sequences.find(s=>s.id===sequenceId)||dataset.sequences.find(s=>s.assetKey)||dataset.sequences[0];
 return {dataset,sequence};
}
export function presentationName(id){
 const labels={
  replica:'汇报① · GS-ICP SLAM / Replica office0',
  'tum-full-gsicp10':'汇报② · GS-ICP SLAM / TUM办公室',
  'ooosplat-office-balanced':'汇报③ · COLMAP + OOOBrush / TUM办公室',
  'medmesh-trans_t2_b-open3d_park_v0500':'演示① · C3VD 横结肠 / ICP＋TSDF',
  'medmesh-cecum_t1_a-open3d_park_v1000':'演示② · C3VD 盲肠 / ICP＋TSDF'
 };
 if(labels[id])return labels[id];
 return findSequence(id).sequence.name;
}
export function selectionCaption(id){return presentationName(id);}
