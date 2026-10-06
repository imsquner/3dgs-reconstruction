import unittest,torch
from quality_losses_v2 import sparse_needle_regularizer
class SparseTests(unittest.TestCase):
 def test_good_surface_does_not_dilute_needle(self):
  needle=torch.tensor([[.3,.005,.005]])
  mixed=torch.cat([needle,torch.tensor([[.3,.3,.001]]).repeat(100,1)])
  self.assertAlmostEqual(sparse_needle_regularizer(needle,torch.tensor([.005])).item(),sparse_needle_regularizer(mixed,torch.cat([torch.tensor([.005]),torch.full((100,),.3)])).item(),places=5)
 def test_no_needles_is_finite_zero(self):
  scales=torch.tensor([[.3,.3,.001]],requires_grad=True)
  loss=sparse_needle_regularizer(scales,torch.tensor([.3]));loss.backward()
  self.assertEqual(loss.item(),0.);self.assertTrue(torch.isfinite(scales.grad).all())
if __name__=='__main__':unittest.main()
