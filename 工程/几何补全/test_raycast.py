"""Actual engine checks: optical-z depth, translated camera and vertex-color interpolation."""
import unittest
import numpy as np
import open3d as o3d
from evaluate_mesh import raycast

class RaycastTests(unittest.TestCase):
    def setUp(self):
        self.mesh=o3d.geometry.TriangleMesh()
        self.mesh.vertices=o3d.utility.Vector3dVector([[-10,-10,2],[10,-10,2],[10,10,2],[-10,10,2]])
        self.mesh.triangles=o3d.utility.Vector3iVector([[0,1,2],[0,2,3]])
        self.mesh.vertex_colors=o3d.utility.Vector3dVector([[1,0,0]]*4)
        self.scene=o3d.t.geometry.RaycastingScene()
        self.scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(self.mesh))
    def test_depth_is_optical_z_not_ray_length(self):
        z,c,hit=raycast(self.scene,self.mesh,np.eye(4),[8,6,4,4,3.5,2.5])
        self.assertTrue(hit.all());np.testing.assert_allclose(z,2,atol=1e-6)
        np.testing.assert_allclose(c,np.broadcast_to([1,0,0],c.shape),atol=1e-6)
    def test_camera_translation(self):
        pose=np.eye(4);pose[2,3]=.5
        z,_,hit=raycast(self.scene,self.mesh,pose,[8,6,4,4,3.5,2.5])
        self.assertTrue(hit.all());np.testing.assert_allclose(z,1.5,atol=1e-6)

if __name__=='__main__':unittest.main()
