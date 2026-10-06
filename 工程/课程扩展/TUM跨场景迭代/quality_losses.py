"""Candidate losses: valid sensor depth and soft needle growth control."""
import torch

def normalized_depth(raw, alpha, background=15.):
    return (raw-background*(1-alpha))/alpha.clamp_min(1e-8)

def valid_depth_loss(pred, reference, alpha):
    valid=(reference>.1)&(reference<3.)&(alpha.detach()>.2)
    error=(pred-reference).abs()
    # Huber in metres; excluded observations contribute no gradient.
    huber=torch.where(error<.05,error.square()/.1,error-.025)
    return (huber*valid).sum()/valid.sum().clamp_min(1)

def needle_regularizer(scales, reference_spacing, reduction=True):
    axes=scales.sort(dim=-1,descending=True).values
    ratio=axes[...,0]/axes[...,1].clamp_min(1e-6)
    growth=axes[...,0]/reference_spacing.clamp_min(1e-6)
    penalty=torch.relu(torch.log(ratio/10.))*torch.relu(torch.log(growth/8.))
    return penalty.mean() if reduction else penalty
