import unittest,numpy as np
from unittest.mock import patch
from quality_rgbd_initial import RgbdInitial
class Initial(unittest.TestCase):
 def test_actual_past_pose_composition_and_depth_copy(self):
  with patch('quality_rgbd_initial.features',return_value=('k','d')),patch('quality_rgbd_initial.measure') as m:
   s=RgbdInitial(np.eye(3),5000,3);image=np.zeros((2,2,3),dtype=np.uint8);depth=np.full((2,2),5000,dtype=np.uint16);pose=np.eye(4);pose[:3,3]=[1,2,3]
   s.update(0,image,depth,pose);depth[:]=0;T=np.eye(4);T[0,3]=.1;m.return_value={'accepted':True,'current_from_previous':T,'inliers':20}
   initial,r=s.update(1,image,depth,pose);np.testing.assert_allclose(initial,pose@np.linalg.inv(T));np.testing.assert_allclose(m.call_args.args[2],1.);np.testing.assert_allclose(pose[:3,3],[1,2,3])
 def test_rejected_measurement_fallback_previous(self):
  with patch('quality_rgbd_initial.features',return_value=('k','d')),patch('quality_rgbd_initial.measure',return_value={'accepted':False}):
   s=RgbdInitial(np.eye(3),5000,3);im=np.zeros((2,2,3));d=np.ones((2,2));p=np.eye(4);s.update(0,im,d,p);v,r=s.update(1,im,d,p);np.testing.assert_array_equal(v,p)
 def test_skip_or_repeat_frame_rejected(self):
  s=RgbdInitial(np.eye(3),5000,3)
  with self.assertRaises(AssertionError):s.update(1,np.zeros((2,2)),np.ones((2,2)),np.eye(4))
if __name__=='__main__':unittest.main()
