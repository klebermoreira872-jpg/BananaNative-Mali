"""Settings › Users (android/app Users.java with android/app/src/jvmtest's UsersJvmTest): the stored list, the first user always the host's fixed one, at most 8 users, the host's
DM_USERS / DM_USER lines (dm/host/hle_account.c reads them) with the names percent-encoded, nothing for the one default user, names cut to 32 bytes, each user's save folder.
javac compiles Users.java with stand-ins for Android's Context and SharedPreferences and for Prefs. Skipped without a JDK."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android/Users.java'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/UsersJvmTest.java'
STUBS = {
    'android/content/Context.java': 'package android.content;\npublic class Context {}\n',
    'android/content/SharedPreferences.java': 'package android.content;\npublic interface SharedPreferences {\n  String getString(String k, String d);\n  int getInt(String k, int d);\n'
                                              '  Editor edit();\n  interface Editor { Editor putString(String k, String v); Editor putInt(String k, int v); void apply(); }\n}\n',
    'dev/nxnative/android/Prefs.java': 'package dev.nxnative.android;\nfinal class Prefs {\n  static final java.util.Map<String, String> M = new java.util.HashMap<>();\n'
                                      '  static android.content.SharedPreferences of(android.content.Context c) { return new android.content.SharedPreferences() {\n'
                                      '    public String getString(String k, String d) { return M.getOrDefault(k, d); }\n    public int getInt(String k, int d) { return d; }\n'
                                      '    public Editor edit() { return new Editor() {\n      public Editor putString(String k, String v) { M.put(k, v); return this; }\n'
                                      '      public Editor putInt(String k, int v) { return this; }\n      public void apply() {}\n    }; } }; }\n}\n',
}


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class UsersJvm(unittest.TestCase):
    def test_users(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for rel, text in STUBS.items():
                p = t / 'stub' / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
            r = subprocess.run(['javac', '-Xlint:all', '-Werror', '-encoding', 'UTF-8', '-d', str(t / 'classes'), str(SRC), str(TEST), *map(str, (t / 'stub').rglob('*.java'))],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(['java', '-cp', str(t / 'classes'), 'dev.nxnative.android.UsersJvmTest'], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(r.stdout.strip(), 'ok')


class UsersSaves(unittest.TestCase):
    def test_saves_tab_acts_on_the_selected_users_save(self):   # #388: Back up / Restore / Import used the first user's save whoever the games start with
        d = SRC.parent
        ui = (d / 'SaveUi.java').read_text(encoding='utf-8')
        body = ui[ui.index('static void backup('):]
        self.assertNotIn('Folders.save(a, g)', body)   # only ready() and gameRunning (the game's own lock) keep the game's save folder
        self.assertEqual(body.count('Folders.userSave(a, g)'), 3)   # backup, exportTo, confirm (Restore and Import both end in confirm)
        self.assertIn('Users.activeSave', (d / 'Folders.java').read_text(encoding='utf-8'))


class UsersScreen(unittest.TestCase):
    def test_profile_pictures(self):   # the picker offers as many round pictures as Users counts, each an emoji on a colour
        ui = (SRC.parent / 'UsersUi.java').read_text(encoding='utf-8')
        n = int(re.search(r'AVATARS = (\d+)', SRC.read_text(encoding='utf-8')).group(1))
        emoji = re.search(r'EMOJI = \{(.*?)\};', ui, re.S).group(1).count('"') // 2
        color = re.search(r'COLOR = \{(.*?)\};', ui, re.S).group(1).count('0xFF')
        self.assertEqual((emoji, color), (n, n))


if __name__ == '__main__':
    unittest.main()
