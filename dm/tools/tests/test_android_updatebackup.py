"""The launcher's automatic save backup before an in-app update installs (UpdateBackup.java with SaveStore and CopyPlan, by android/app/src/jvmtest's
UpdateBackupJvmTest; UpdateBackupUi and Updater run it on the phone): a changed save is backed up, an unchanged or empty one skipped, a backups folder in app
storage or without All files access refused, a save in use skipped, nothing deleted or overwritten. Skipped without a JDK."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/UpdateBackupJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class UpdateBackupJvm(unittest.TestCase):
    def test_jvm(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            srcs = [SRC / f'{n}.java' for n in ('UpdateBackup', 'SaveStore', 'CopyPlan')]
            r = subprocess.run(['javac', '-Xlint:all,-try', '-Werror', '-encoding', 'UTF-8', '-d', str(t / 'classes'), *map(str, srcs), str(TEST)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            (t / 'run').mkdir()
            r = subprocess.run(['java', '-cp', str(t / 'classes'), 'dev.nxnative.android.UpdateBackupJvmTest', str(t / 'run')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
            self.assertEqual(r.stdout.strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
