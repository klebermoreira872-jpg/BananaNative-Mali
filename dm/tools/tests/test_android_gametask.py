"""The game's task (android/README.md, "The game's task"; docs/reference/threads.md, "Two game instances"): GameActivity has a task affinity of its own and leaves
Recents when it finishes, its screen's finish ends the :game process, a screen for another game while one runs says "stop it first" (RunGuard, on the JVM with
android/app/src/jvmtest's RunGuardJvmTest), and Stop goes through the activity's own end. The JVM part is skipped without a JDK."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/RunGuardJvmTest.java'
MANIFEST = REPO / 'android/app/src/main/AndroidManifest.xml'


class Manifest(unittest.TestCase):
    def test_game_has_its_own_task(self):
        act = re.search(r'<activity\s[^>]*android:name="\.GameActivity"[^>]*>', MANIFEST.read_text())
        self.assertIsNotNone(act)
        a = act.group(0)
        self.assertIn('android:launchMode="singleTask"', a)
        self.assertIn('android:process=":game"', a)
        self.assertIn('android:taskAffinity="${applicationId}.game"', a)   # never Home's task: the icon cannot close the game's screen
        self.assertIn('android:autoRemoveFromRecents="true"', a)   # no empty card left once the game ends
        self.assertNotIn('excludeFromRecents', a)   # the game's card is the one Recents keeps


class Wiring(unittest.TestCase):
    def test_screen_end_ends_process(self):
        g = (SRC / 'GameActivity.java').read_text(encoding='utf-8')
        self.assertIn('RunGuard.endsProcess(isFinishing(), isChangingConfigurations())', g)
        self.assertIn('RunGuard.otherRunning(hostRunning', g)
        self.assertIn('finishAndRemoveTask()', g)
        self.assertIn('GameReturn.homeInRecents(this, false)', g)
        self.assertIn('GameReturn.homeInRecents(this, true)', (SRC / 'MainActivity.java').read_text(encoding='utf-8'))
        # Stop ends the screen and its task first (a bare kill left an empty card in Recents that started the game again)
        p = (SRC / 'SidePanel.java').read_text(encoding='utf-8')
        self.assertIn('((GameActivity) act).stop()', p)


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class Guard(unittest.TestCase):
    def test_run_guard(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', d, str(SRC / 'RunGuard.java'), str(TEST)], check=True, capture_output=True, text=True)
            r = subprocess.run(['java', '-cp', d, 'dev.nxnative.android.RunGuardJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(r.stdout.startswith('ok '), r.stdout)


if __name__ == '__main__':
    unittest.main()
