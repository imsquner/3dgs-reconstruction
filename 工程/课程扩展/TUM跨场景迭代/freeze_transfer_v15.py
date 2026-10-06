"""Create transfer metadata only after complete numeric and nine-view acceptance."""
import argparse,json
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
from freeze_parameters import from_manifest
from transfer_batch_v6 import validate_freeze
B=Path(__file__).resolve().parent;E=B.parents[1]

def create(review_path,output_path):
 state=B/'状态/online-opacity-full-v15.json'
 assert state.exists() and json.loads(state.read_text())['stage']=='complete','Full coordinator must finish before freezing'
 base='local-tum-quality-barrierfull-original-b10-v15'
 candidate='local-tum-quality-barrierfull-birth-b20-v15'
 result=audit(base,candidate,'development')
 assert result['all_numeric_gates'] is True,'Full numeric acceptance required'
 review=Path(review_path).resolve();review_relative=review.relative_to(B)
 full=json.loads((B/'协议/online-opacity-full-v15-frozen.json').read_text())
 assert any(job[-1]==candidate for job in full['jobs'])
 scripts=dict(full['scripts'])
 for name in ['transfer_batch_v6.py','freeze_transfer_v15.py','portable_protocol.py','test_transfer_gate_v6.py','freeze_parameters.py','test_freeze_parameters.py']:
  scripts[name]=sha256(B/name)
 assert all(sha256(B/name)==digest for name,digest in scripts.items())
 run=E/'运行'/candidate
 saved=json.loads((run/'state.json').read_text());assert saved['status']=='complete'
 assert all(sha256(run/name)==digest for name,digest in saved['artifacts'].items())
 frozen=dict(status='accepted_for_transfer',seed=0,input_fps=5.,
  quality_parameters=from_manifest(json.loads((run/'manifest.json').read_text())),
  scripts=scripts,source_manifest_sha256=sha256(B/'来源/source-manifest.json'),calibrated_projection_sha256=sha256(E/'服务器/projection.py'),
  development=dict(base=base,candidate=candidate,map_sha256=result['map_sha256'],
   visual_review=review_relative.as_posix(),visual_review_sha256=sha256(review),
   tracking_positions_reference_sha256=sha256(run/'tracking-birth-positions.npy'),
   tracking_covariance_reference_sha256=sha256(run/'tracking-covariance-reference.npz'),tracking_opacity_reference_sha256=sha256(run/'tracking-birth-opacity.npy')),
  protocols={scene:dict(protocol_sha256=sha256(B/'协议'/f'{scene}.json'),observations_sha256=sha256(B/'协议'/f'{scene}-observations.json')) for scene in ['tum-desk','replica-office0']},
  scope='Single-seed per-observation CUDA-budget boundary development acceptance; scheduled5FPS input is not5FPS reconstruction. Transfer inputs were not used for selection; no transfer success or artifact-area percentage claim.')
 validate_freeze(frozen)
 output=Path(output_path).resolve();output.relative_to(B)
 if output.exists():assert json.loads(output.read_text())==frozen,'Never overwrite a different freeze'
 else:atomic_json(output,frozen)
 print('TRANSFER_V15_FREEZE_VALIDATED',output,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 create(a.review,a.output)
