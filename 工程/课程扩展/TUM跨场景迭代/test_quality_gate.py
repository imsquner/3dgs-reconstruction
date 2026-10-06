import unittest
from quality_gate import numeric_gate

class Gates(unittest.TestCase):
 def test_rgb_cannot_hide_geometry_failure(self):
  b={'psnr_db':20.,'ssim':.7,'coverage':.99}
  c={'psnr_db':21.,'ssim':.71,'coverage':.95}
  self.assertFalse(numeric_gate(b,c,.1,.09,'development')['all_numeric_gates'])
 def test_geometry_cannot_hide_rgb_regression(self):
  b={'psnr_db':20.,'ssim':.7,'coverage':.99}
  c={'psnr_db':20.6,'ssim':.69,'coverage':.99}
  self.assertFalse(numeric_gate(b,c,.1,.09,'development')['all_numeric_gates'])
 def test_development_and_transfer_differ(self):
  b={'psnr_db':20.,'ssim':.7,'coverage':.99}
  c={'psnr_db':19.9,'ssim':.698,'coverage':.98}
  self.assertFalse(numeric_gate(b,c,.1,.102,'development')['all_numeric_gates'])
  self.assertTrue(numeric_gate(b,c,.1,.102,'transfer')['all_numeric_gates'])
 def test_missing_common_is_not_pass(self):
  b={'psnr_db':20.,'ssim':.7,'coverage':.99}
  c={'psnr_db':21.,'ssim':.71,'coverage':.99}
  self.assertIsNone(numeric_gate(b,c,None,None,'development')['all_numeric_gates'])

if __name__=='__main__':unittest.main()
