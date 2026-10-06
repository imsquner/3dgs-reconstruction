"""Development v2: normalize sparse needle terms by active count."""
from quality_losses import needle_regularizer
def sparse_needle_regularizer(scales, reference_spacing):
    terms=needle_regularizer(scales,reference_spacing,reduction=False)
    return terms.sum()/(terms.detach()>0).sum().clamp_min(1)
