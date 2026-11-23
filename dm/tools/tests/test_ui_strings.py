"""dm/tools/ui_strings.py: the inventory of the launcher's hard-coded UI literals finds the strings in the listed Ui calls, dialogs, toasts and label arrays,
ignores comments, keys and resource text, and counts per file."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui_strings as U  # noqa: E402

SAMPLE = '''package x;
class A {
    // Ui.small(c, "Not a string in code")
    void f(Context c) {
        Ui.section(c, "Appearance");
        new Ui.Setting(c, "x", "Theme choice", v -> g("some_key")).value("Light or dark").badge("Experimental");
        new AlertDialog.Builder(c).setTitle("Delete the copy?").setPositiveButton("Delete", null).setNegativeButton(R.string.cancel, null);
        Toast.makeText(c, flag ? "Saved it" : "Not saved", Toast.LENGTH_SHORT).show();
        view.setContentDescription("Banana Native");
        Ui.small(c, "Installed: " + name);
        Ui.small(c, Tx.s(R.string.home_ready));
        Log.i("TAG", "a log line that stays");
        String[] labels = {"Large screen", "Small"};
        Prefs.get("env_name");
    }
}
'''


class Inventory(unittest.TestCase):
    def scan(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'A.java'
            p.write_text(text, encoding='utf-8')
            return [lit for _, lit in U.scan(p)]

    def test_finds_the_listed_calls(self):
        got = self.scan(SAMPLE)
        for want in ('Appearance', 'Theme choice', 'Light or dark', 'Experimental', 'Delete the copy?', 'Delete', 'Saved it', 'Not saved', 'Banana Native',
                     'Installed: ', 'Large screen'):
            self.assertIn(want, got)

    def test_ignores_comments_keys_logs_and_resources(self):
        got = self.scan(SAMPLE)
        for no in ('Not a string in code', 'some_key', 'a log line that stays', 'env_name', 'TAG'):
            self.assertNotIn(no, got)

    def test_the_tree_is_scanned(self):
        inv = U.inventory()
        self.assertTrue(any(f.endswith('MainActivity.java') for f in inv))

    def test_no_new_hard_coded_ui_text(self):
        # the guard: a user-visible literal in the listed Ui calls goes to res/values/strings.xml (Tx.s(R.string.key)), not into the code
        bad = U.violations()
        self.assertEqual(bad, [], 'hard-coded UI text (move it to strings.xml, or list it in dm/tools/ui_strings_allow.txt with a reason):\n'
                         + '\n'.join(f'{f}:{ln}: {lit}' for f, ln, lit in bad))

    def test_allow_list_has_no_stale_lines(self):
        have = {(f, lit) for f, hits in U.inventory().items() for _, lit in hits}
        stale = sorted(U.allow() - have)
        self.assertEqual(stale, [], 'allow-list lines whose literal is gone from the code (delete them)')

    def test_allow_list_lines_have_a_file_and_text(self):
        for ln in U.ALLOW.read_text(encoding='utf-8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                self.assertIn('\t', ln, f'allow-list line without a tab: {ln!r}')


if __name__ == '__main__':
    unittest.main()
