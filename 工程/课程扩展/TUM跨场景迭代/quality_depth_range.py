"""Same fixed depth loss; valid maximum comes from sensor/dataset metadata."""
import torch
def valid_depth_loss_range(pred,reference,alpha,max_depth=3.):
    if max_depth<=.1:raise ValueError('Invalid depth interval')
    valid=(reference>.1)&(reference<max_depth)&(alpha.detach()>.2)
    error=(pred-reference).abs()
    huber=torch.where(error<.05,error.square()/.1,error-.025)
    return (huber*valid).sum()/valid.sum().clamp_min(1)
