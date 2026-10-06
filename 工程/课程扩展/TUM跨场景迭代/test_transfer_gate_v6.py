import copy,unittest
from transfer_batch_v6 import validate_parameters,validate_visual,validate_projection,E
from quality_core import sha256
class FrozenV15Parameters(unittest.TestCase):
 def setUp(self):
  self.parameters=dict(depth_weight=.05,coverage_weight=.05,needle_weight=.002,growth_weight=0.,growth_factor=8.,tracking_covariance='raw-gicp',tracking_positions='birth',tracking_opacity='birth',mapping_schedule='observation-barrier')
 def test_accepts_current_declared_rule(self):validate_parameters(self.parameters)
 def test_rejects_every_changed_parameter(self):
  for key in self.parameters:
   changed=copy.deepcopy(self.parameters);changed[key]='invalid'
   with self.assertRaises(AssertionError):validate_parameters(changed)
 def test_rejects_missing_or_extra(self):
  changed=copy.deepcopy(self.parameters);changed.pop('tracking_opacity')
  with self.assertRaises(AssertionError):validate_parameters(changed)
  changed=copy.deepcopy(self.parameters);changed['tracking_geometry']='raw-map'
  with self.assertRaises(AssertionError):validate_parameters(changed)
class FixedViews(unittest.TestCase):
 def setUp(self):
  self.views=[dict(train_index=i,offset_local_x_m=x,fewer_visible_artifacts=True,table_chair_preserved=True) for i in [0,1126,2252] for x in [0.,.2,.4]]
  self.review=dict(map_sha256=['a','b'],views=copy.deepcopy(self.views))
 def test_accepts_exact_all9(self):validate_visual(self.review,['a','b'],self.views)
 def test_rejects_failure_unknown_missing_reordered(self):
  for key in ['fewer_visible_artifacts','table_chair_preserved']:
   for value in [False,None]:
    bad=copy.deepcopy(self.review);bad['views'][4][key]=value
    with self.assertRaises(AssertionError):validate_visual(bad,['a','b'],self.views)
  for views in [self.views[:-1],list(reversed(self.views)),self.views[:-1]+[self.views[0]]]:
   with self.assertRaises(AssertionError):validate_visual(dict(self.review,views=views),['a','b'],self.views)
 def test_rejects_wrong_maps(self):
  with self.assertRaises(AssertionError):validate_visual(self.review,['a','c'],self.views)
class ProjectionPin(unittest.TestCase):
 def test_actual_pin_and_reject_other(self):
  validate_projection({'calibrated_projection_sha256':sha256(E/'服务器/projection.py')})
  with self.assertRaises(AssertionError):validate_projection({'calibrated_projection_sha256':'0'*64})
if __name__=='__main__':unittest.main()
