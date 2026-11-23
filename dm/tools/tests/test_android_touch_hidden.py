"""Hiding single on-screen controls in the layout editor (#539): TouchHidden on the JVM (android/app/src/jvmtest's TouchHiddenJvmTest) and that TouchControls is wired to it:
a tap in the editor toggles, the hidden set is kept with the layout of the screen shape, Reset clears it, play leaves the hidden controls out of the host's layout. Nothing
hidden is the default. Skipped without a JDK (the JVM part)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/TouchHiddenJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class TouchHiddenJvm(unittest.TestCase):
    def test_hidden_set(self):
        tmp = Path(tempfile.mkdtemp(prefix='touchhidden_'))
        try:
            r = subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', str(tmp), str(SRC / 'TouchHidden.java'), str(TEST)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(['java', '-cp', str(tmp), 'dev.nxnative.android.TouchHiddenJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(r.stdout.strip(), 'ok')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TouchHiddenWiring(unittest.TestCase):
    tc = (SRC / 'TouchControls.java').read_text(encoding='utf-8')

    def test_kept_per_screen_shape_and_reset(self):
        self.assertIn('prefs().getString("hidden@" + prof, "")', self.tc)
        self.assertIn('e.putString("hidden@" + prof, TouchHidden.encode(hidden));', self.tc)
        self.assertIn('hidden = new java.util.LinkedHashSet<>();\n        relayout(); saveLayout();', self.tc, 'Reset the controls shows every control again')

    def test_editor_taps_toggle_and_play_leaves_them_out(self):
        self.assertIn('if (act == MotionEvent.ACTION_UP && !moved && tapI >= 0) toggleHidden(tapI);', self.tc)
        self.assertIn('if (!editing) hideFromLayout();', self.tc)
        self.assertIn('relayout();   // every control, the hidden ones too', self.tc, 'the editor opens with all of them')

    def test_every_control_has_a_key_and_the_default_hides_none(self):
        keys = {'zl', 'l', 'zr', 'r', 'minus', 'plus', 'stick0', 'dpad', 'l3', 'a', 'b', 'x', 'y', 'stick1', 'r3'}
        for k in keys: self.assertIn(f'"{k}"', self.tc)
        self.assertIn('private java.util.Set<String> hidden = new java.util.LinkedHashSet<>();', self.tc)


if __name__ == '__main__':
    unittest.main()
