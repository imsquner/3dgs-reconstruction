export const officeVersions=[
 {number:'00',label:'原始完整地图｜毛刺基线保留',assetKey:'office',observations:true},
 {number:'01',label:'原版短段｜240帧·正常预算',assetKey:'office-exp-01',observations:false},
 {number:'02',label:'原版短段｜240帧·增加预算',assetKey:'office-exp-02',observations:false},
 {number:'03',label:'本组工程优化①｜RGB-D姿态初值',assetKey:'office-exp-03',observations:false},
 {number:'04',label:'本组工程优化②｜损失与跟踪反馈＋RGB-D初值',assetKey:'office-exp-04',observations:false}
];
export function resolveVersion(id,number){if(id!=='office')return null;const v=officeVersions.find(v=>v.number===number);if(!v)throw new Error('未知实验版本');return v;}
