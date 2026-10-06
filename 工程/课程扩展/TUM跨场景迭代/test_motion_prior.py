import unittest,numpy as np
from scipy.spatial.transform import Rotation
from quality_motion_prior import predict
class Motion(unittest.TestCase):
 def test_constant_translation_and_unequal_timestamps(self):
  a=np.eye(4);c=a.copy();c[0,3]=.1
  self.assertAlmostEqual(predict([a,c],[0.,1.],1.5)[0,3],.15)
 def test_rotation(self):
  a=np.eye(4);c=a.copy();c[:3,:3]=Rotation.from_euler('z',10,degrees=True).as_matrix()
  self.assertAlmostEqual(Rotation.from_matrix(predict([a,c],[0.,1.],2.)[:3,:3]).as_euler('xyz',degrees=True)[2],20.)
 def test_only_latest_two_poses_and_no_mutation(self):
  a=np.eye(4);c=a.copy();c[0,3]=.1;before=c.copy()
  x=predict([a,c],[0.,1.],2.);bad=np.full((4,4),np.nan)
  self.assertTrue(np.allclose(x,predict([bad,a,c],[-1.,0.,1.],2.)));self.assertTrue(np.array_equal(c,before))
 def test_fallback_and_clamp(self):
  a=np.eye(4);c=a.copy();c[0,3]=.1
  self.assertTrue(np.array_equal(predict([c],[0.],1.),c))
  self.assertTrue(np.array_equal(predict([a,c],[0.,0.],1.),c))
  self.assertAlmostEqual(predict([a,c],[0.,1.],100.)[0,3],.3)
if __name__=='__main__':unittest.main()
