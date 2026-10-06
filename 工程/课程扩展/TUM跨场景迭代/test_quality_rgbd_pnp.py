import unittest,numpy as np,cv2
from quality_rgbd_pnp import solve_relative,world_from_relative
class PnP(unittest.TestCase):
 def test_direction_and_outlier_rejection(self):
  rng=np.random.RandomState(7);points=rng.uniform([-1,-.6,1],[1,.6,3],(120,3));K=np.array([[535.,0,320],[0,539.,240],[0,0,1]])
  rv=np.array([.02,-.025,.01]);tv=np.array([.03,.005,-.01]);uv=cv2.projectPoints(points,rv,tv,K,None)[0].reshape(-1,2);uv[:20]=rng.uniform([0,0],[640,480],(20,2))
  result=solve_relative(points,uv,K);self.assertTrue(result['accepted']);self.assertLess(result['inliers'],120);self.assertGreater(result['inliers'],90)
  T=np.eye(4);T[:3,:3]=cv2.Rodrigues(rv)[0];T[:3,3]=tv
  np.testing.assert_allclose(result['current_from_previous'],T,atol=1e-5)
  previous=np.eye(4);previous[:3,3]=[1,2,3];np.testing.assert_allclose(world_from_relative(previous,T),previous@np.linalg.inv(T))
 def test_empty_returns_unaccepted(self):self.assertFalse(solve_relative(np.empty((0,3)),np.empty((0,2)),np.eye(3))['accepted'])
 def test_inputs_not_mutated(self):
  points=np.ones((4,3));pixels=np.ones((4,2));original=points.copy();solve_relative(points,pixels,np.eye(3));np.testing.assert_array_equal(points,original)
if __name__=='__main__':unittest.main()
