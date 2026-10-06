import copy,unittest
from transfer_batch_v5 import validate_visual,validate_freeze,validate_projection,E
from quality_core import sha256

class CalibratedProjection(unittest.TestCase):
 def test_accepts_actual_projection_pin(self):
  validate_projection({'calibrated_projection_sha256':sha256(E/'服务器/projection.py')})
 def test_rejects_other_projection(self):
  with self.assertRaises(AssertionError):validate_projection({'calibrated_projection_sha256':'0'*64})

class VisualGate(unittest.TestCase):
 def setUp(self):
  self.views=[dict(train_index=i,offset_local_x_m=x,fewer_visible_artifacts=True,table_chair_preserved=True) for i in [0,120,239] for x in [0.,.2,.4]]
  self.review=dict(map_sha256=['a','b'],views=copy.deepcopy(self.views))
 def test_accepts_complete_matching_views(self):validate_visual(self.review,['a','b'],self.views)
 def test_rejects_missing_and_duplicate(self):
  for views in [self.views[:-1],self.views[:-1]+[self.views[0]]]:
   with self.assertRaises(AssertionError):validate_visual(dict(self.review,views=views),['a','b'],self.views)
 def test_rejects_unknown_or_failed_preservation(self):
  for value in [None,False]:
   bad=copy.deepcopy(self.review);bad['views'][4]['table_chair_preserved']=value
   with self.assertRaises(AssertionError):validate_visual(bad,['a','b'],self.views)
 def test_rejects_other_map_and_camera(self):
  with self.assertRaises(AssertionError):validate_visual(self.review,['a','c'],self.views)
  bad=copy.deepcopy(self.review);bad['views'][8]['train_index']=240
  with self.assertRaises(AssertionError):validate_visual(bad,['a','b'],self.views)

class FreezeVersion(unittest.TestCase):
 def test_rejects_old_covariance_freeze(self):
  with self.assertRaises(AssertionError):
   validate_freeze({'status':'accepted_for_transfer','quality_parameters':{'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':.01,'growth_factor':8.}})

class CovarianceMode(unittest.TestCase):
 def test_rejects_render_covariance_candidate(self):
  for mode in ['optimized','birth-render']:
   with self.assertRaises(AssertionError):
    validate_freeze({'status':'accepted_for_transfer','quality_parameters':{'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':0.,'growth_factor':8.,'tracking_covariance':mode,'tracking_positions':'birth'}})

class GeometryMode(unittest.TestCase):
 def test_rejects_covariance_only_freeze(self):
  with self.assertRaises(AssertionError):
   validate_freeze({'status':'accepted_for_transfer','quality_parameters':{'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':0.,'growth_factor':8.,'tracking_covariance':'raw-gicp','tracking_positions':'optimized'}})

class PreviousRawMap(unittest.TestCase):
 def test_rejects_previous_unpruned_raw_map(self):
  with self.assertRaises(AssertionError):
   validate_freeze({'status':'accepted_for_transfer','quality_parameters':{'depth_weight':.05,'coverage_weight':.05,'needle_weight':.002,'growth_weight':0.,'growth_factor':8.,'tracking_covariance':'raw-gicp','tracking_geometry':'raw-map'}})

if __name__=='__main__':unittest.main()
