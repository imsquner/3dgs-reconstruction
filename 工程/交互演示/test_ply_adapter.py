import unittest,tempfile
from pathlib import Path
import numpy as np
from ply_adapter import adapt_xyzw_to_wxyz

class ConversionTest(unittest.TestCase):
 def test_preserves_positions_scales_and_rotates_header_quaternion_order(self):
  names=['x','y','z','nx','ny','nz','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3']
  header=('ply\nformat binary_little_endian 1.0\nelement vertex 1\n'+''.join('property float '+n+'\n' for n in names)+'end_header\n').encode()
  a=np.arange(17,dtype='<f4');a[13:]=[0,0,2**-.5,2**-.5]
  with tempfile.TemporaryDirectory() as temp:
   src=Path(temp)/'src.ply';dst=Path(temp)/'dst.ply';original=header+a.tobytes();src.write_bytes(original)
   report=adapt_xyzw_to_wxyz(src,dst);b=np.frombuffer(dst.read_bytes()[len(header):],dtype='<f4')
   np.testing.assert_array_equal(b[:13],a[:13]);np.testing.assert_array_equal(b[13:],[a[16],a[13],a[14],a[15]])
   self.assertEqual(src.read_bytes(),original);self.assertEqual(report['max_covariance_error'],0)
if __name__=='__main__':unittest.main()
