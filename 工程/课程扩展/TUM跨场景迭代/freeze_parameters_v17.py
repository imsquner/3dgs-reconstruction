"""Export exact v17 tracking prior; not an acceptance/freeze decision."""
import ast
from pathlib import Path
from freeze_parameters import from_manifest as base_parameters
from quality_core import sha256
B=Path(__file__).resolve().parent
def from_manifest(manifest):
 q=manifest['quality_args'];assert 'pose_prior' in q,'v17 requires explicit prior'
 prior=q['pose_prior'];assert prior in ['previous','constant-velocity'],'Unknown prior'
 name='quality_motion_prior.py';actual=sha256(B/name)
 assert manifest['quality_module_hashes'][name]==actual,'Executed motion source differs'
 tree=ast.parse((B/name).read_text())
 limits=[n.args[0] for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='min']
 assert len(limits)==1,'Ambiguous motion bounds';limit=float(ast.literal_eval(limits[0]));assert limit>0
 return {**base_parameters(manifest),'pose_prior':prior,'motion_prediction_enabled':prior=='constant-velocity','motion_ratio_upper_bound':limit,'motion_module_sha256':actual,'motion_semantics':'Latest two estimated poses and RGB timestamps; constant world translation and rotation increment; invalid timestamp/first pose fallback previous.'}
