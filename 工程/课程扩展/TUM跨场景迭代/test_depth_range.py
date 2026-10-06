import unittest,torch
from quality_losses import valid_depth_loss
from quality_depth_range import valid_depth_loss_range
class RangeTests(unittest.TestCase):
 def test_tum_identical_loss_and_gradient(self):
  p=torch.tensor([2.1,4.2,0.],requires_grad=True);r=torch.tensor([2.,4.,0.]);alpha=torch.ones(3)
  old=valid_depth_loss(p,r,alpha);new=valid_depth_loss_range(p,r,alpha,3.)
  self.assertEqual(old.item(),new.item())
  self.assertTrue(torch.equal(torch.autograd.grad(old,p,retain_graph=True)[0],torch.autograd.grad(new,p)[0]))
 def test_replica_keeps_distant_valid_depth(self):
  p=torch.tensor([4.2],requires_grad=True);r=torch.tensor([4.]);loss=valid_depth_loss_range(p,r,torch.ones(1),12.);loss.backward()
  self.assertGreater(loss.item(),0.);self.assertGreater(p.grad.item(),0.)
 def test_invalid_depth_excluded(self):
  p=torch.tensor([1.,13.],requires_grad=True);loss=valid_depth_loss_range(p,torch.tensor([0.,13.]),torch.ones(2),12.);loss.backward()
  self.assertEqual(loss.item(),0.);self.assertTrue(torch.equal(p.grad,torch.zeros(2)))
if __name__=='__main__':unittest.main()
