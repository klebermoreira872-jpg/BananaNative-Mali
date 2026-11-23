"""Which kind of release the running launcher is (BuildKind.java with android/app/src/jvmtest's BuildKindJvmTest): preview, hotfix, critical, major or unknown,
from the version name and -PnxReleaseKind; the short note the logs carry. Skipped without a JDK."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android/BuildKind.java'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/BuildKindJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class BuildKindJvm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        subprocess.run(['javac', '-Xlint:all', '-Werror', '-encoding', 'UTF-8', '-d', cls.tmp.name, str(SRC), str(TEST)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def java(self, *a):
        r = subprocess.run(['java', '-cp', self.tmp.name, 'dev.nxnative.android.BuildKindJvmTest', *a], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.rstrip('\n').split(' ', 1)[1] if ' ' in r.stdout else ''

    def test_kind(self):
        self.assertEqual(self.java('kind', '0.3.51-preview', '-'), 'preview')      # the name alone says preview
        self.assertEqual(self.java('kind', '0.3.51-preview', 'preview'), 'preview')
        self.assertEqual(self.java('kind', '0.3.51', 'hotfix'), 'hotfix')
        self.assertEqual(self.java('kind', '0.3.51', 'critical'), 'critical')
        self.assertEqual(self.java('kind', '0.3.50', 'major'), 'major')
        self.assertEqual(self.java('kind', '0.3.50', '-'), '')                     # a test build: unknown
        self.assertEqual(self.java('kind', '0.3.50', 'bogus'), '')

    def test_base_and_notes(self):
        self.assertEqual(self.java('base', '0.3.51-preview'), '0.3.51')
        self.assertEqual(self.java('base', '0.3.51'), '0.3.51')
        self.assertEqual(self.java('log', 'hotfix'), ', hotfix build')
        self.assertEqual(self.java('log', 'preview'), ', preview build')
        self.assertEqual(self.java('log', 'major'), '')
        self.assertEqual(self.java('log', '-'), '')
        self.assertEqual(self.java('hotfix', 'critical'), 'true')
        self.assertEqual(self.java('hotfix', 'major'), 'false')


if __name__ == '__main__':
    unittest.main()
