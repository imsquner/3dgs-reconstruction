"""Exact mask used by pinned GS-ICP prune_large_and_transparent."""
import torch
def original_prune_mask(scales,opacity,extent):
    mask=(opacity<.005).squeeze(-1)
    if extent is not None:mask=torch.logical_or(mask,scales.max(dim=1).values>.1*extent)
    return mask
