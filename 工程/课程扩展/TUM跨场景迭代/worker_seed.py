"""Explicit seeding at every spawn worker entry, before its first sample."""
import random,numpy as np,torch

def seed_worker(seed):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
