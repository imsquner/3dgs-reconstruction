import unittest,torch
from quality_coverage import valid_coverage_loss

class CoverageTests(unittest.TestCase):
 def test_only_undercovered_valid_depth_gets_opacity_gradient(self):
  alpha=torch.tensor([.5,.995,.1],requires_grad=True)
  loss=valid_coverage_loss(alpha,torch.tensor([1.,2.,0.]),3.)
  self.assertAlmostEqual(float(loss),.245,places=6);loss.backward()
  self.assertTrue(torch.equal(alpha.grad,torch.tensor([-.5,0.,0.])))
 def test_missing_and_out_of_range_depth_do_not_push_opacity(self):
  alpha=torch.tensor([.2,.2],requires_grad=True)
  loss=valid_coverage_loss(alpha,torch.tensor([0.,4.]),3.);loss.backward()
  self.assertEqual(float(loss),0.);self.assertEqual(float(alpha.grad.abs().sum()),0.)
 def test_replica_range_retains_far_sensor_supervision(self):
  alpha=torch.tensor([.5],requires_grad=True)
  self.assertEqual(float(valid_coverage_loss(alpha,torch.tensor([4.]),3.)),0.)
  self.assertAlmostEqual(float(valid_coverage_loss(alpha,torch.tensor([4.]),12.)),.49,places=6)

if __name__=='__main__':unittest.main()
