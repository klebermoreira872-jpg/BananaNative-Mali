"""Home's tile order (Reorder games) on the JVM: javac compiles GameOrder with android/app/src/jvmtest's GameOrderJvmTest (sorting by id, new games last, removed
games dropped, stable on repeat, a merged entry keeping its place). Also a source check: a long press on a game's tile opens the Move left / Move right menu
(a preparing tile keeps its job sheet), and a controller's Y does the same on the focused tile. Skipped without a JDK (the JVM part)."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/GameOrderJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class GameOrderJvm(unittest.TestCase):
    def test_order(self):
        tmp = Path(tempfile.mkdtemp(prefix='gameorder_'))
        try:
            r = subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', str(tmp), str(SRC / 'GameOrder.java'), str(TEST)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(['java', '-cp', str(tmp), 'dev.nxnative.android.GameOrderJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r'^ok \d+')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class GameOrderSource(unittest.TestCase):
    main = (SRC / 'MainActivity.java').read_text()

    def test_long_press_opens_the_menu(self):
        card = self.main[self.main.index('private View gameCard(Game g)'):]
        card = card[:card.index('private View emptyCard') if 'private View emptyCard' in card else 3000]
        self.assertRegex(card, r'setOnLongClickListener\(v -> \{ optionsMenu\(g\)')
        menu = self.main[self.main.index('private void optionsMenu(Game g)'):]
        menu = menu[:menu.index('// ---- Move')]
        for key in ('home_move_game', 'game_cover_set', 'home_delete_game_menu'):
            self.assertIn('R.string.' + key, menu)

    def test_move_mode_keys(self):
        move = self.main[self.main.index('private boolean moveKey'):]
        move = move[:move.index('// ---- The hint bar')]
        for key in ('KEYCODE_DPAD_LEFT', 'KEYCODE_DPAD_UP', 'KEYCODE_BUTTON_A', 'KEYCODE_BUTTON_B' if False else 'isBack'):
            self.assertIn(key, move)
        self.assertIn('KEYCODE_BUTTON_X', self.main[self.main.index('public boolean dispatchKeyEvent'):])

    def test_add_game_button_is_always_there(self):
        # #381: with no game the round Add game button was hidden and the welcome card had no button of its own
        refresh = self.main[self.main.index('void refresh() {'):]
        refresh = refresh[:refresh.index('Reorder games') if 'Reorder games' in refresh else 4000]
        self.assertNotIn('View.GONE', refresh[:refresh.index('workTiles.clear()')])
        self.assertIn('addFab.setVisibility(View.VISIBLE)', refresh)
        self.assertIn('addFab.requestFocus()', refresh)
        self.assertNotIn('emptyCard', self.main)

    def test_preparing_tile_keeps_its_sheet(self):
        work = self.main[self.main.index('private void workTile(View c)'):]
        work = work[:work.index('workTick();')]
        self.assertIn('c.setOnLongClickListener(v -> { sheet.onClick(v); return true; })', work)

    def test_pad_button_opens_it(self):
        key = self.main[self.main.index('public boolean dispatchKeyEvent'):]
        key = key[:key.index('return super.dispatchKeyEvent')]
        self.assertIn('KEYCODE_BUTTON_Y', key)
        self.assertIn('performLongClick', key)

    def test_home_sorts_by_stored_order(self):
        self.assertRegex(self.main, r'GameOrder\.sort\(games, Prefs\.gameOrder\(this\)')
        prefs = (SRC / 'Prefs.java').read_text()
        self.assertIn('static List<String> gameOrder(Context c)', prefs.replace('java.util.List', 'List'))


if __name__ == '__main__':
    unittest.main()
