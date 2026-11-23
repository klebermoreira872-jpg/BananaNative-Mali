"""The Prepare job's card is shown only in its sheet (Ondevice.sheet), never on Home: the source checks (no JVM, no phone)."""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
J = REPO / 'android/app/src'
ONDEVICE = (J / 'ondevice/java/dev/nxnative/android/Ondevice.java').read_text()
MAIN = (J / 'main/java/dev/nxnative/android/MainActivity.java').read_text()


class PrepareSheet(unittest.TestCase):
    def test_home_never_attaches_the_panel_view(self):
        m = re.search(r'static void attach\(MainActivity a\) \{(.*?)\n    \}', ONDEVICE, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn('addView', m.group(1))
        self.assertNotIn('Ondevice.attach(this, content', MAIN)
        self.assertIn('Ondevice.attach(this);', MAIN)
        # the only place the card's view goes into a parent is the sheet's scroll view
        self.assertNotRegex(ONDEVICE, r'addView\((panel\.)?view[,)]')
        self.assertIn('View v = panel.view;', ONDEVICE)
        self.assertEqual(ONDEVICE.count('sv.addView(v);'), 1)

    def test_sheet_opens_for_a_needed_tap(self):
        self.assertIn('static String needsTap(Job j, boolean alive)', ONDEVICE)
        for kind in ('"failed"', '"goon"'):
            self.assertIn('return ' + kind, ONDEVICE)
        self.assertIn('autoSheet(needsTap(job, alive));', ONDEVICE)
        self.assertRegex(ONDEVICE, r'if \(news && resumed && !sheetShowing\(\)\) sheet\(a\);')
        # a job that only runs asks for nothing
        self.assertNotRegex(ONDEVICE, r'return "running"')

    def test_sheet_closes_when_the_job_goes(self):
        self.assertRegex(ONDEVICE, r'view\.setVisibility\(View\.GONE\);[^\n]*closeSheet\(\)')

    def test_sheet_is_a_closable_bottom_sheet(self):
        self.assertIn('Tx.s(R.string.common_close)', ONDEVICE)
        self.assertIn('setCanceledOnTouchOutside(true)', ONDEVICE)
        self.assertIn('Gravity.BOTTOM', ONDEVICE)
        self.assertIn('R.string.home_tile_details', MAIN)

    def test_a_started_prepare_opens_the_sheet_but_an_automatic_update_does_not(self):
        self.assertIn('userAsked = !card;', ONDEVICE)
        self.assertRegex(ONDEVICE, r'if \(userAsked\) \{ userAsked = false;')

    def test_no_text_under_the_tall_tile(self):
        self.assertNotIn('portraitName', MAIN)

    def test_tile_opens_the_sheet(self):
        self.assertIn('Ondevice.sheet(this)', MAIN)


if __name__ == '__main__':
    unittest.main()
