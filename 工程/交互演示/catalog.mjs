// Stable identifiers are independent of Chinese labels and asset filenames.
const seq=(id,name,summary,status,assetKey=null,observations=false)=>({id,name,summary,status,assetKey,observations});
export const catalog=[
 {id:'tum',number:'01',category:'natural',name:'TUM RGB-D',summary:'真实室内桌面与办公室',sequences:[
  seq('desk','rgbd_dataset_freiburg1_desk','桌面近景','实验完成，尚未接入'),
  seq('office','rgbd_dataset_freiburg3_long_office_household','办公室连续扫描 · 原始毛刺版','原始版保留','office',true),
  seq('xyz','rgbd_dataset_freiburg1_xyz','平移运动序列','实验完成，尚未接入')]},
 {id:'replica',number:'02',category:'natural',name:'Replica',summary:'合成房间与办公室',sequences:[
  seq('room0','room0','房间','开发实验，尚未接入'),
  seq('replica','office0','办公室','已接入演示','replica')]},
 {id:'endoslam',number:'03',category:'medical',name:'EndoSLAM',summary:'合成腔道与真实离体内镜',sequences:[
  seq('unity','Unity colon','合成腔道 · 本地别名，发布原名待核验','局部演示','unity'),
  seq('highcam','HighCam','真实离体内镜 · 本地别名，发布原名待核验','长序列失败，诊断保留')]},
 {id:'c3vd',number:'04',category:'medical',name:'C3VD',summary:'实体结肠模型内镜',sequences:[
  seq('c3vd-trans-t2-b','trans_t2_b','横结肠模型 · 纹理2 · 序列b','开发结果，尚未接入')]}
];
export function datasetsFor(category){return catalog.filter(d=>d.category===category);}
export function datasetLabel(d){return `${d.number} · ${d.name}｜${d.summary}`;}
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
export function selectionCaption(id){const {dataset,sequence}=findSequence(id);return `${dataset.category==='natural'?'自然场景':'医学场景'} / ${dataset.number} ${dataset.name} / ${sequence.name}`;}
