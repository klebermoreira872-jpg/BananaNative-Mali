"""internal/tools/issue_ledger.py: the ledger parses, every note has the keys, and `check` reports a missing block, a newer comment and who spoke last
(offline: Forgejo data is passed in). Skipped where internal/ is absent (the public repository)."""
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TOOL = REPO / 'internal/tools/issue_ledger.py'
KEYS = ('Reporter', 'Seen', 'State', 'Cause', 'Evidence', 'Replied', 'Fix', 'Next')


def load():
    spec = importlib.util.spec_from_file_location('issue_ledger', TOOL); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


@unittest.skipUnless(TOOL.exists(), 'no internal/ folder (public repository)')
class Ledger(unittest.TestCase):
    def test_blocks_are_complete(self):
        m = load(); opened, archived = m.load_notes(); blocks = {**opened, **archived}
        self.assertTrue(blocks)
        self.assertFalse(set(opened) & set(archived), 'a note is both open and archived')
        for n, b in blocks.items():
            for k in KEYS: self.assertIn(k, b, f'#{n}: no "- {k}:" line')
            self.assertIn(b['State'].split()[0], m.STATES, f'#{n}: State {b["State"]!r}')
            self.assertTrue(b['Reporter'].find(f'issues/{n}') >= 0, f'#{n}: the Reporter line has no Forgejo link')
            self.assertTrue(m.seen_id(b) >= 0)

    def test_check(self):
        m = load()
        blocks = m.parse('# #5 a\n- Seen: 10 (x)\n- State: waiting-reporter\n\n# #6 b\n- Seen: 20\n- State: ours\n\n# #7 c\n- Seen: 1\n- State: ours\n')
        issues = [{'number': 5, 'comments': 2, 'title': 'a'}, {'number': 6, 'comments': 1, 'title': 'b'}, {'number': 8, 'comments': 0, 'title': 'd'}]
        com = {5: [{'id': 10, 'user': {'login': 'moceure'}}], 6: [{'id': 21, 'user': {'login': 'player'}}], 8: []}
        lines, bad = m.check(blocks, issues, lambda n: com[n])
        text = '\n'.join(lines)
        self.assertIn('waiting for the reporter', lines[0]); self.assertIn('NEW (comment 21 by player)', lines[1]); self.assertIn('NO-NOTE', lines[2])
        self.assertIn('#7', lines[3]); self.assertEqual(bad, 3, text)   # 6 new, 8 no block, 7 closed but still "ours"

    def test_no_block_section(self):
        m = load()
        text = '# #5 a\n- State: fixed (shipped)\n\n## No file yet\n\n- #8: feature request\n- #9: bug, not investigated\n'
        self.assertEqual(m.parse_noblock(text), {8: 'feature request', 9: 'bug, not investigated'})
        self.assertEqual(m.parse(text)[5]['State'], 'fixed (shipped)')
        issues = [{'number': 8, 'comments': 0, 'title': 'd'}, {'number': 10, 'comments': 0, 'title': 'e'}]
        lines, bad = m.check(m.parse(text), issues, lambda n: [], m.parse_noblock(text))
        self.assertIn('no note yet', lines[0]); self.assertIn('NO-NOTE', lines[1])
        self.assertEqual(bad, 2)   # #10 has no note; #5 is fixed and closed: ARCHIVE

    def test_open_issues_all_covered_by_ledger_text(self):
        m = load(); text = m.LEDGER.read_text(encoding='utf-8'); opened, archived = m.load_notes(); nb = m.parse_noblock(text)
        self.assertFalse((set(opened) | set(archived)) & set(nb), 'an issue has a note and is also in "No file yet"')

    def test_archive_moves_notes_and_fixes_links(self):
        m = load()
        self.assertEqual(m.fix_links('[a](../../docs/x.md) [b](../topics/y.md) [c](z.md)', True), '[a](../../../docs/x.md) [b](../../topics/y.md) [c](z.md)')
        self.assertEqual(m.fix_links('[a](../../../docs/x.md) [b](../../topics/y.md)', False), '[a](../../docs/x.md) [b](../topics/y.md)')


if __name__ == '__main__':
    unittest.main()
