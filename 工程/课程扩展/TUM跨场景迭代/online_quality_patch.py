"""Candidate online loss injection; retains upstream insertion/pruning order."""
import torch
from quality_spacing import install_spacing_tracking
from quality_losses import normalized_depth
from quality_losses_v2 import sparse_needle_regularizer
from quality_depth_range import valid_depth_loss_range

def patch_candidate_mapping(code,mapping,depth_max):
 install_spacing_tracking(mapping.GaussianModel)
 def online_candidate_loss(mapper,camera,image,raw_depth,rgb,depth):
  white=torch.ones_like(mapper.background)
  white_image=mapping.render_3(camera,mapper.gaussians,mapper.pipe,white,
                              training_stage=mapper.training_stage)['render']
  alpha=1-(white_image-image).mean(0).clamp(0,1)
  model=mapper.gaussians
  assert len(model.quality_initial_spacing)==len(model.get_scaling)
  shape=sparse_needle_regularizer(model.get_scaling,model.quality_initial_spacing)
  return (.8*(image-rgb).abs().mean()+.2*(1-mapping.ssim(image,rgb)[1])
          +.01*valid_depth_loss_range(normalized_depth(raw_depth,alpha),depth,alpha,depth_max)
          +.002*shape)
 mapping.online_candidate_loss=online_candidate_loss
 start='            mask = (gt_depth_image>0.)'
 end='            loss.backward()'
 assert code.count(start)==1 and code.count(end)==1,'Upstream loss layout changed'
 begin=code.index(start);finish=code.index(end,begin)
 replacement=('            loss = online_candidate_loss(self, viewpoint_cam, image, depth_image, '
              'gt_image, gt_depth_image)\n            assert torch.isfinite(loss), "Nonfinite online candidate loss"\n\n')
 return code[:begin]+replacement+code[finish:]
