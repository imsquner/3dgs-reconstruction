"""Report completed stages only; unfinished comparison stays explicitly partial."""
import json,argparse
from pathlib import Path
import numpy as np
from plyfile import PlyData
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
p=argparse.ArgumentParser();p.add_argument('--plan',default='full-refinement-frozen.json');a=p.parse_args();pruned=a.plan=='pruned-refinement-frozen.json';stem='带剪枝对照阶段记录' if pruned else '完整对照阶段记录'
plan=json.loads((B/'协议'/a.plan).read_text());names=[plan['base']]+[j[2] for j in plan['jobs']];rows=[];pending=[]
for name in names:
 R=E/'运行'/name
 if not (R/'评价/metrics.json').exists():pending.append(name);continue
 m=json.loads((R/'评价/metrics.json').read_text());assert m['signature']['map']==sha256(R/'scene.ply')
 v=PlyData.read(R/'scene.ply')['vertex'].data;s=np.sort(np.exp(np.stack([v[f'scale_{i}'] for i in range(3)],-1)),axis=-1);opacity=1/(1+np.exp(-v['opacity']))
 shape={'gaussians':len(v),'needle_smax_gt_0p2_ratio_gt10_opacity_gt0p5':int(((s[:,2]>.2)&(s[:,2]/np.maximum(s[:,1],1e-6)>10)&(opacity>.5)).sum())}
 row={'run':name,'means':m['means'],'shape':shape,'label':'原GS-ICP在线基线' if name==plan['base'] else ('相同上游剪枝的离线损失对照' if pruned else '固定拓扑无剪枝损失对照（非完整上游行为）')}
 state=json.loads((R/'state.json').read_text())
 if name==plan['base']:
  summary=json.loads((R/'summary.json').read_text());mapping=json.loads((R/'mapping-summary.json').read_text())
  row['runtime']={'phase':'online','wall_seconds':summary['wall_seconds'],'render_backward_iterations':mapping['mapping_iterations'],'peak_torch_allocated_bytes':mapping['peak_cuda_allocated_bytes'],'gradient_bearing_optimizer_step_calls':None}
 else:
  row['runtime']={'phase':'offline','wall_seconds':state['elapsed_seconds'],'render_backward_iterations':state['step'],'peak_torch_allocated_bytes':state.get('peak_cuda_allocated_bytes'),'gradient_bearing_optimizer_step_calls':state.get('gradient_bearing_optimizer_step_calls')}
 if (R/'评价/common-depth.json').exists():row['common_depth']=json.loads((R/'评价/common-depth.json').read_text())['means']
 rows.append(row)
 if name!=plan['base']:
  state=json.loads((R/'state.json').read_text());(R/'实验记录.md').write_text('\n'.join(['# '+name,'',('完整办公室离线同剪枝规则开发对照，训练仅使用基线估计关键帧相机，不添加留出观测。' if pruned else '完整办公室离线固定拓扑开发对照，训练仅使用基线估计关键帧相机，不添加留出观测。'),'优化耗时秒：'+str(state['elapsed_seconds']),'留出指标：'+json.dumps(m['means'],ensure_ascii=False),'形状描述：'+json.dumps(shape,ensure_ascii=False),'共同深度：'+json.dumps(row.get('common_depth','尚未完成'),ensure_ascii=False),'配置/哈希manifest.json；优化器checkpoint.pt；评价metrics.json；对应阶段日志位于课程扩展/TUM跨场景迭代/日志。','尚未完成全组三预算比较、全部自由视角审阅与跨序列测试，不能作为最终改善结论。']),encoding='utf-8')
  with (R/'实验记录.md').open('a',encoding='utf-8') as f:f.write('\n实际预算与资源：'+json.dumps(row['runtime'],ensure_ascii=False)+'\n有梯度Adam调用未知时为null，不把render/backward迭代数冒充实际更新。Torch峰值不包含全部原生分配或其他进程。\n')
if rows:
 reference=rows[0]['means']
 for row in rows[1:]:
  m=row['means'];common=row.get('common_depth')
  row['development_checks']={'psnr_delta_db':m['psnr_db']-reference['psnr_db'],'ssim_delta':m['ssim']-reference['ssim'],'coverage_delta_pp':100*(m['coverage']-reference['coverage']),
   'primary_rgb_threshold_met':m['psnr_db']-reference['psnr_db']>=.5 or m['ssim']-reference['ssim']>=.01,
   'coverage_threshold_met':m['coverage']>=reference['coverage']-.02,
   'common_mae_ratio':common['candidate']['common_mae_m']/common['base']['common_mae_m'] if common else None,
   'common_mae_threshold_met':common['candidate']['common_mae_m']<=1.05*common['base']['common_mae_m'] if common else None,
   'status':'numeric checks only; other RGB metric, all fixed-view appearance, trajectory, online stage and frozen transfer still require review; not final acceptance'}
for row in rows:
 R=E/'运行'/row['run']
 if (R/'performance-audit-10min.json').exists():
  row['performance_snapshot']=json.loads((R/'performance-audit-10min.json').read_text())
  with (R/'实验记录.md').open('a',encoding='utf-8') as f:f.write('\n长时资源证据见performance-audit-10min.json；瞬时整卡资源不等于实验独占峰值。\n')
atomic_json(B/(stem+'.json'),{'rows':rows,'pending':pending,'status':'partial' if pending else 'metrics_complete_visual_transfer_pending','scope':'Complete stages only. Online building and offline refinement timing separate. Needle descriptors do not prove screen artifact reduction.'})
scope='离线两方采用相同上游剪枝规则、相同观测和估计相机，缓存512MiB；它们仍不是在线插点重建实验。更新迭代与实际有梯度Adam调用分别记录，额外渲染计算成本单列。' if pruned else '这些离线组不含上游每200步剪枝，不能当作完整原方案的公平比较。保留作损失/拓扑失控诊断，另补相同上游剪枝规则的三预算对照。'
lines=['# '+stem,'','状态：'+('partial' if pending else '数值齐全，视觉与迁移仍待验收'),'',scope,'','|版本|PSNR dB|SSIM|覆盖 %|MAE cm|RMSE cm|针状数|','|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
 m=row['means'];lines.append(f"|{row['run']}|{m['psnr_db']:.4f}|{m['ssim']:.5f}|{100*m['coverage']:.3f}|{100*m['depth_mae_m']:.3f}|{100*m['depth_rmse_m']:.3f}|{row['shape']['needle_smax_gt_0p2_ratio_gt10_opacity_gt0p5']}|")
lines+=['','待完成：'+', '.join(pending),'','不得把PSNR单项提高称全面改善。统一251留出帧，最终还需共同深度、全部固定自由视角桌椅/毛刺与冻结迁移门。原始地图不删。']
lines+=['','## 实际预算与资源','','|版本|阶段|秒|render/backward迭代|有梯度Adam调用|Torch峰值MiB|','|---|---|---:|---:|---:|---:|']
for row in rows:
 r=row['runtime'];peak=r['peak_torch_allocated_bytes'];lines.append(f"|{row['run']}|{r['phase']}|{r['wall_seconds']:.2f}|{r['render_backward_iterations']}|{r['gradient_bearing_optimizer_step_calls']}|{peak/2**20 if peak is not None else None}|")
lines+=['','预算相同指迭代相同，不指耗时或FLOPs相同；候选损失额外渲染一次。原剪枝会替换Parameter，该迭代的梯度不用于Adam更新。在线基线未记录实际Adam调用，明确为None。','', '## 开发数值检查（不是最终验收）']
for row in rows[1:]:lines+=['','- '+row['run']+'：'+json.dumps(row['development_checks'],ensure_ascii=False)]
(B/(stem+'.md')).write_text('\n'.join(lines),encoding='utf-8');print('FULL_REPORT_PARTIAL',len(rows),pending,flush=True)
