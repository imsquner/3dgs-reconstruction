import unittest
import numpy as np
from geometry_contract import validate_pose, validate_split, depth_reliability


class ContractTests(unittest.TestCase):
    def test_mirror_pose_rejected(self):
        p = np.eye(4); p[0, 0] = -1
        with self.assertRaises(ValueError): validate_pose(p)

    def test_camera_world_inverse(self):
        p = np.eye(4); p[:3, 3] = [1, 2, 3]
        self.assertTrue(np.allclose(validate_pose(p) @ p, np.eye(4)))

    def test_holdout_depth_overlap_rejected(self):
        with self.assertRaises(ValueError):
            validate_split([{'source_frame': 0, 'depth_id': 'same'}], [{'source_frame': 10, 'depth_id': 'same'}])

    def test_frame_order_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            validate_split([{'source_frame': 3, 'depth_id': 'a'}, {'source_frame': 2, 'depth_id': 'b'}], [])

    def test_invalid_depth_and_far_depth(self):
        d = np.array([[0, np.nan, 0.5, 4.0]])
        m = depth_reliability(d, 'raw', 3.0)
        self.assertEqual(m.tolist(), [[False, False, True, False]])

    def test_edge_mask_does_not_remove_flat_thin_patch(self):
        d = np.ones((7, 7)); d[:, 4:] = 2
        m = depth_reliability(d, 'edge', 3.0)
        self.assertTrue(m[:, :3].all())
        self.assertFalse(m[:, 3:5].any())
        self.assertTrue(m[:, 5:].all())


if __name__ == '__main__': unittest.main()
