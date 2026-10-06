import json,sys
from pathlib import Path
import numpy as np
from plyfile import PlyData
from quality_core import atomic_json
B=Path(__file__).resolve().parent;E=B.parents[1]
names=['local-tum-quality-base240-v1','local-tum-quality-refine-original-1000-v1','local-tum-quality-refine-original-2000-v1','local-tum-quality-refine-improved-2000-v1','local-tum-quality-refine-improved-shape-2000-v2']
rows=[]
for name in names:
 R=E/'运行'/name;m=json.loads((R/'评价/metrics.json').read_text());v=PlyData.read(R/'scene.ply')['vertex'].data
 scale=np.sort(np.exp(np.stack([v[f'scale_{i}'] for i in range(3)],-1)),axis=-1)
 opacity=1/(1+np.exp(-v['opacity']))
 stats={'gaussians':len(v),'needle_smax_gt_0p2_ratio_gt10_opacity_gt0p5':int(((scale[:,2]>.2)&(scale[:,2]/np.maximum(scale[:,1],1e-6)>10)&(opacity>.5)).sum()),'smax_p99_m':float(np.quantile(scale[:,2],.99))}
 rows.append({'run':name,'means':m['means'],'shape':stats})
base=rows[0]['means'];improved=rows[-1]['means'];delta={k:improved[k]-base[k] for k in base}
gate={'rgb':(delta['psnr_db']>=.5 or delta['ssim']>=.01) and delta['psnr_db']>=-.2 and delta['ssim']>=-.005,'coverage':delta['coverage']>=-.02,'depth_mae':improved['depth_mae_m']<=base['depth_mae_m']*1.05}
atomic_json(B/'短段消融汇总.json',{'rows':rows,'improved_minus_base':delta,'numeric_gates':gate,'scope':'240-frame development only; no free-view/whole-map/cross-scene pass claim. Needle count is descriptive, not an objective surface accuracy metric. RMSE separately reported.'})
lines=['# 240帧离线精修开发对照','','统一输入：同一64543高斯地图、28估计关键帧、seed0、固定拓扑；26帧留出不参与训练。','','|版本|PSNR dB|SSIM|覆盖 %|MAE cm|RMSE cm|针状异常数|','|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
 m=row['means'];lines.append(f"|{row['run']}|{m['psnr_db']:.4f}|{m['ssim']:.5f}|{100*m['coverage']:.3f}|{100*m['depth_mae_m']:.3f}|{100*m['depth_rmse_m']:.3f}|{row['shape']['needle_smax_gt_0p2_ratio_gt10_opacity_gt0p5']}|")
lines+=['','短段数值门：'+json.dumps(gate,ensure_ascii=False),'','改进组PSNR/SSIM上升，但RMSE增加，不能称所有几何指标都提高。当前MAE按各版本自身覆盖像素计算，后续完整场景比较须补共同有效像素对照，避免掩码选择影响。自由视角无真值，只能定性审阅；桌椅保留及毛刺改善仍需完整场景检查。','', '所有原图保留；此阶段无增点/剪枝，不等同完整原版在线重建或实时性能。']
(B/'短段消融报告.md').write_text('\n'.join(lines),encoding='utf-8')
for row in rows[1:]:
 R=E/'运行'/row['run'];state=json.loads((R/'state.json').read_text());(R/'实验记录.md').write_text('\n'.join(['# '+row['run'],'','固定拓扑离线开发实验，训练相机为估计位姿，仅使用基线关键帧。','配置与输入哈希：manifest.json；完整恢复：checkpoint.pt；指标：评价/metrics.json。','优化累计秒数：'+str(state['elapsed_seconds']),'指标：'+json.dumps(row['means'],ensure_ascii=False),'形状描述：'+json.dumps(row['shape'],ensure_ascii=False),'结论边界与全组比较见 ../../课程扩展/TUM跨场景迭代/短段消融报告.md。']),encoding='utf-8')
print(json.dumps({'gates':gate,'delta':delta,'shape':[r['shape'] for r in rows]},ensure_ascii=False),flush=True)
