import unittest,torch
from quality_losses import normalized_depth,valid_depth_loss,needle_regularizer
class LossTests(unittest.TestCase):
 def test_background_depth_does_not_bias_surface(self):
  self.assertAlmostEqual(normalized_depth(torch.tensor(5.25),torch.tensor(.75)).item(),2.,places=5)
 def test_missing_depth_has_zero_gradient(self):
  pred=torch.tensor([2.,4.],requires_grad=True);ref=torch.tensor([2.,0.]);loss=valid_depth_loss(pred,ref,torch.ones(2));loss.backward()
  self.assertEqual(pred.grad[1].item(),0.)
 def test_flat_surface_is_not_needle(self):
  scale=torch.tensor([[.3,.3,.001],[.3,.005,.005]],requires_grad=True)
  terms=needle_regularizer(scale,torch.tensor([.3,.005]),reduction=False)
  self.assertEqual(terms[0].item(),0.);self.assertGreater(terms[1].item(),0.)
 def test_regularizer_shrinks_long_axis(self):
  scale=torch.tensor([[.3,.005,.005]],requires_grad=True);needle_regularizer(scale,torch.tensor([.005])).backward()
  self.assertGreater(scale.grad[0,0].item(),0.)
if __name__=='__main__':unittest.main()
