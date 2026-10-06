"""Ray coverage supervision from valid training depth only."""
import torch

def valid_coverage_loss(alpha,reference,depth_max,target=.99):
 valid=(reference>.1)&(reference<depth_max)
 return (torch.relu(target-alpha)*valid).sum()/valid.sum().clamp_min(1)
