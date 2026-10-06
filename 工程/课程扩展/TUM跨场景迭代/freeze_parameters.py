"""Resolve candidate metadata from actual args plus SHA-verified source defaults."""
import ast
from pathlib import Path
from quality_core import sha256
B=Path(__file__).resolve().parent

def from_manifest(manifest):
 q=manifest['quality_args'];assert q['variant']=='improved-shape'
 keys=['depth_weight','coverage_weight','growth_weight','tracking_covariance','tracking_positions','tracking_opacity','mapping_schedule']
 assert all(k in q for k in keys),'Missing actual run parameters'
 sources={}
 for name in ['quality_growth.py','online_quality_patch_v3.py']:
  assert sha256(B/name)==manifest['quality_module_hashes'][name],'Run source changed'
  sources[name]=ast.parse((B/name).read_text())
 fn=next(n for n in sources['quality_growth.py'].body if isinstance(n,ast.FunctionDef) and n.name=='growth_regularizer')
 defaults=dict(zip([a.arg for a in fn.args.args[-len(fn.args.defaults):]],fn.args.defaults));factor=float(ast.literal_eval(defaults['factor']))
 shape_weights=[float(ast.literal_eval(n.left)) for n in ast.walk(sources['online_quality_patch_v3.py']) if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Mult) and isinstance(n.right,ast.Name) and n.right.id=='shape' and isinstance(n.left,ast.Constant)]
 assert len(shape_weights)==1 and factor>1
 needle=shape_weights[0]
 assert q.get('growth_factor',factor)==factor and q.get('needle_weight',needle)==needle,'Reported constant differs from executed source'
 return {**{k:q[k] for k in keys},'growth_factor':factor,'needle_weight':needle}
