import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import cv2,numpy as np
import publish_history as publisher

class InputPublicationTests(unittest.TestCase):
 def test_actual_training_inputs_only_and_original_maps_preserved(self):
  self.assertTrue(hasattr(publisher,'publish_input_frames'),'all actual input frames need independent publication')
  with tempfile.TemporaryDirectory() as tmp:
   web=Path(tmp);run=web/'run';run.mkdir();out=web/'assets/history-published/replica/run';out.mkdir(parents=True)
   rows=[]
   for i in range(3):
    rgb=run/f'{i}.jpg';depth=run/f'{i}.png'
    rgb.write_bytes(cv2.imencode('.jpg',np.full((4,6,3),i*50,np.uint8))[1].tobytes())
    depth.write_bytes(cv2.imencode('.png',np.full((4,6),1000,np.uint16))[1].tobytes())
    rows.append(dict(source_frame=i,training_frame=None if i==1 else i//2,heldout=i==1,rgb=str(rgb),depth=str(depth),rgb_sha256=publisher.digest(rgb),depth_sha256=publisher.digest(depth),scene_time_seconds=i/30))
   manifest=run/'inputs.json';manifest.write_text(json.dumps(dict(dataset='replica',rows=rows,source_frames=3,training_frames=2)))
   (run/'frames.jsonl').write_text('\n'.join(json.dumps(dict(frame=i,estimated_c2w=np.eye(4).tolist())) for i in range(2)))
   meta=dict(run_id='run',scope='full',input_fps=5,indices=[0,2],snapshots=[dict(sha256='original',ply='/map.ply')],input_manifest_sha256=publisher.digest(manifest))
   (out/'index.json').write_text(json.dumps(meta))
   with patch.object(publisher,'WEB',web):result=publisher.publish_input_frames(run,manifest,'replica')
   self.assertEqual([r['source_frame'] for r in result['input_frames']],[0,2]);self.assertEqual(result['snapshots'],meta['snapshots'])
   self.assertEqual(result['input_frames'][1]['input_rgb_sha256'],rows[2]['rgb_sha256'])
   self.assertTrue((web/result['input_frames'][1]['depth']).is_file())
   rows[2]['scene_time_seconds']=999;manifest.write_text(json.dumps(dict(dataset='replica',rows=rows,training_frames=2)))
   with patch.object(publisher,'WEB',web),self.assertRaises(ValueError):publisher.publish_input_frames(run,manifest,'replica')
   rows[2]['rgb_sha256']='bad';manifest.write_text(json.dumps(dict(dataset='replica',rows=rows,training_frames=2)))
   meta['input_manifest_sha256']=publisher.digest(manifest);(out/'index.json').write_text(json.dumps(meta))
   with patch.object(publisher,'WEB',web),self.assertRaises(ValueError):publisher.publish_input_frames(run,manifest,'replica')

if __name__=='__main__':unittest.main()
