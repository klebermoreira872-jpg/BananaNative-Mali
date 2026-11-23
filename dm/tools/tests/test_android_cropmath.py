"""The cover crop's arithmetic (CropMath.java with android/app/src/jvmtest's CropMathJvmTest): the crop stays inside the picture and keeps the frame's aspect,
pan stops at the edges, zoom holds the point under the finger and is capped, the output is at most 1024 px and never enlarged. Skipped without a JDK."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/CropMathJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class CropMathJvm(unittest.TestCase):
    def test_crop(self):
        tmp = Path(tempfile.mkdtemp(prefix='cropmath_'))
        try:
            r = subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', str(tmp), str(SRC / 'CropMath.java'), str(TEST)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(['java', '-cp', str(tmp), 'dev.nxnative.android.CropMathJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('CropMathJvmTest ok', r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
