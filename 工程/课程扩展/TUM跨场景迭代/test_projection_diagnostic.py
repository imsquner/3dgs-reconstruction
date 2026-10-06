import unittest,numpy as np
from projection_diagnostic import project_covariance
class ProjectionTests(unittest.TestCase):
 def test_identity_camera_elongation(self):
  xy,cov,z=project_covariance(np.array([[0.,0.,2.]]),np.array([[.3,.01,.01]]),np.array([[0.,0.,0.,1.]]),np.eye(4),[640,480,300,300,320,240])
  self.assertTrue(np.allclose(xy,[[320,240]]));self.assertAlmostEqual(cov[0,0,0],2025.3);self.assertAlmostEqual(cov[0,1,1],2.55)
 def test_quaternion_xyzw_rotation(self):
  _,cov,_=project_covariance(np.array([[0.,0.,2.]]),np.array([[.3,.01,.01]]),np.array([[0.,0.,2**-.5,2**-.5]]),np.eye(4),[640,480,300,300,320,240])
  self.assertAlmostEqual(cov[0,1,1],2025.3);self.assertAlmostEqual(cov[0,0,0],2.55)
if __name__=='__main__':unittest.main()
