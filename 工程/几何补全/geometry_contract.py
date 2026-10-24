"""Geometry-side contracts; original protocol and maps remain immutable."""
import numpy as np


def validate_pose(pose):
    p = np.asarray(pose, dtype=float)
    if p.shape != (4, 4) or not np.isfinite(p).all():
        raise ValueError('Invalid pose shape or finite values')
    r = p[:3, :3]
    if not np.allclose(p[3], [0, 0, 0, 1], atol=1e-6) or not np.allclose(r.T @ r, np.eye(3), atol=5e-4) or abs(np.linalg.det(r)-1) > 5e-4:
        raise ValueError('Non-rigid or mirrored pose')
    return np.linalg.inv(p)


def validate_split(train, holdout):
    ids = [r['source_frame'] for r in train]
    if ids != sorted(set(ids)):
        raise ValueError('Training frame IDs must be unique and ordered')
    if {r['depth_id'] for r in train} & {r['depth_id'] for r in holdout}:
        raise ValueError('Holdout depth overlap')


def depth_reliability(depth_m, variant, trunc, edge_jump=0.05):
    z = np.asarray(depth_m)
    valid = np.isfinite(z) & (z > 0.1) & (z < trunc)
    if variant in ('raw', 'range', 'bilateral', 'consistent', 'combined'):
        return valid
    if variant != 'edge':
        raise ValueError('Unknown depth variant')
    bad = np.zeros(z.shape, dtype=bool)
    for axis in (0, 1):
        a = [slice(None), slice(None)]; b = a.copy()
        a[axis] = slice(None, -1); b[axis] = slice(1, None)
        a, b = tuple(a), tuple(b)
        jump = valid[a] & valid[b] & (np.abs(z[a]-z[b]) > edge_jump)
        bad[a] |= jump; bad[b] |= jump
    return valid & ~bad
