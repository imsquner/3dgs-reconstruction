"""Create transfer metadata only after complete numeric and nine-view acceptance."""
import argparse,json
from pathlib import Path
from quality_core import atomic_json,sha256
from quality_gate import audit
from transfer_batch_v5 import validate_freeze
B=Path(__file__).resolve().parent;E=B.parents[1]

def create(review_path,output_path):
 assert json.loads((B/'状态/online-position-full-v10.json').read_text())['stage']=='complete','Full coordinator must finish before freezing'
 base='local-tum-quality-online-full-original-b10-v6'
 candidate='local-tum-quality-online-full-birthraw-b20-v10'
 result=audit(base,candidate,'development')
 assert result['all_numeric_gates'] is True,'Full numeric acceptance required'
 review=Path(review_path).resolve();review_relative=review.relative_to(B)
 full=json.loads((B/'协议/online-position-full-v10-frozen.json').read_text())
 assert full['run']==candidate
 scripts=dict(full['scripts'])
 for name in ['transfer_batch_v5.py','freeze_transfer_v10.py','portable_protocol.py','test_transfer_gate_v5.py']:
  scripts[name]=sha256(B/name)
 assert all(sha256(B/name)==digest for name,digest in scripts.items())
 run=E/'运行'/candidate
 saved=json.loads((run/'state.json').read_text());assert saved['status']=='complete'
 assert all(sha256(run/name)==digest for name,digest in saved['artifacts'].items())
 frozen=dict(status='accepted_for_transfer',seed=0,input_fps=5.,
  quality_parameters={key:full[key] for key in ['depth_weight','coverage_weight','needle_weight','growth_weight','growth_factor','tracking_covariance','tracking_positions']},
  scripts=scripts,source_manifest_sha256=sha256(B/'来源/source-manifest.json'),calibrated_projection_sha256=sha256(E/'服务器/projection.py'),
  development=dict(base=base,candidate=candidate,map_sha256=result['map_sha256'],
   visual_review=review_relative.as_posix(),visual_review_sha256=sha256(review),
   tracking_positions_reference_sha256=sha256(run/'tracking-birth-positions.npy'),
   tracking_covariance_reference_sha256=sha256(run/'tracking-covariance-reference.npz')),
  protocols={scene:dict(protocol_sha256=sha256(B/'协议'/f'{scene}.json'),observations_sha256=sha256(B/'协议'/f'{scene}-observations.json')) for scene in ['tum-desk','replica-office0']},
  scope='Single-seed asynchronous development acceptance. Transfer inputs were not used for selection; no transfer success or artifact-area percentage claim.')
 validate_freeze(frozen)
 output=Path(output_path).resolve();output.relative_to(B)
 if output.exists():assert json.loads(output.read_text())==frozen,'Never overwrite a different freeze'
 else:atomic_json(output,frozen)
 print('TRANSFER_V10_FREEZE_VALIDATED',output,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 create(a.review,a.output)
