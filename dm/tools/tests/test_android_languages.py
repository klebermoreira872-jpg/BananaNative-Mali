"""The launcher's languages (android/README.md, Languages): every R.string / R.plurals / R.array the code uses is in the English res/values, each language the picker
lists has a values-<lang>/strings.xml with the same keys and placeholders (dm/tools/i18n_xml.py), locales_config.xml and Languages.LIST agree, the manifest is
set for per-app languages and right-to-left, and the redesigned screens use start/end margins."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/tools'))
import i18n_xml as X  # noqa: E402

APP = REPO / 'android/app/src'
JAVA = [*(APP / 'main/java').rglob('*.java'), *(APP / 'ondevice/java').rglob('*.java')]
RES = APP / 'main/res'


def english_text():
    return re.sub(r'<!--.*?-->', '', (RES / 'values/strings.xml').read_text(encoding='utf-8'), flags=re.S)


class Resources(unittest.TestCase):
    def test_no_key_twice_in_english(self):
        names = re.findall(r'<(?:string|plurals|string-array) name="([A-Za-z0-9_]+)"', english_text())
        self.assertEqual(sorted({n for n in names if names.count(n) > 1}), [])

    def test_every_key_the_code_asks_for_exists(self):
        xml = english_text() + (RES / 'values/languages.xml').read_text(encoding='utf-8')
        have = set(re.findall(r'name="([A-Za-z0-9_]+)"', xml))
        used = set()
        for f in JAVA:
            used |= set(re.findall(r'R\.(?:string|plurals|array)\.([A-Za-z0-9_]+)', f.read_text(encoding='utf-8')))
        missing = sorted(u for u in used if u not in have and not u.startswith(('app_',)) and (RES / 'values/strings.xml').read_text().find(u) < 0)
        self.assertEqual(missing, [])

    def test_translations_have_the_keys_and_placeholders(self):
        r = subprocess.run([sys.executable, str(REPO / 'dm/tools/i18n_xml.py'), 'check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_languages_agree(self):
        cfg = set(re.findall(r'android:name="([^"]+)"', (RES / 'xml/locales_config.xml').read_text(encoding='utf-8')))
        lst = set(re.findall(r'new Lang\("([^"]+)"', (APP / 'main/java/dev/nxnative/android/Languages.java').read_text(encoding='utf-8')))
        self.assertEqual(cfg, lst)
        for tag in lst - {'en'}:
            folder = 'values-' + tag.replace('-', '-r')
            self.assertTrue((RES / folder / 'strings.xml').is_file(), folder)
            self.assertIn('machine translated, unreviewed', (RES / folder / 'strings.xml').read_text(encoding='utf-8'))
            self.assertIn('name="lang_' + tag.lower().replace('-', '_') + '"', (RES / 'values/languages.xml').read_text(encoding='utf-8'))

    def test_manifest(self):
        m = (RES.parent / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:localeConfig="@xml/locales_config"', m)
        self.assertIn('android:supportsRtl="true"', m)

    def test_screens_use_start_and_end(self):
        # the redesigned screens mirror for Arabic: no one-sided left/right margins or gravity (the game's own HUD in GameActivity and Overlay is placed by pixel and stays)
        for name in ('MainActivity', 'Ui', 'GameSettings', 'Folders', 'SidePanel', 'SaveUi', 'StorageUi'):
            t = (APP / f'main/java/dev/nxnative/android/{name}.java').read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'Gravity\.(LEFT|RIGHT)\b', t), name)
            self.assertIsNone(re.search(r'\b(?<!\.)\w+\.(leftMargin|rightMargin) = [^=]*;', re.sub(r'\w+\.leftMargin = \w+\.rightMargin = ', '', t)), name)


def java_literal(t):
    return re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: chr(int(m.group(1)[1:], 16)) if len(m.group(1)) == 5 else {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), t)


class Words(unittest.TestCase):
    def test_words_english_is_the_resource_english(self):
        # Words.s("key", "English") in the classes that run without Android: the English there is the key's fallback and must be the English of res/values
        en = X.parse(X.EN)
        bad = []
        n = 0
        for f in (j for j in JAVA if j.name != 'Words.java'):
            for key, text in re.findall(r'Words\.s\("([a-z0-9_]+)",\s*"((?:[^"\\]|\\.)*)"', f.read_text(encoding='utf-8')):
                n += 1
                if key not in en['strings']: bad.append(f'{f.name}: {key} is not in strings.xml')
                elif en['strings'][key] != java_literal(text): bad.append(f'{f.name}: {key}: code says {java_literal(text)!r}, strings.xml {en["strings"][key]!r}')
        self.assertGreater(n, 100)
        self.assertEqual(bad, [])


class Picker(unittest.TestCase):
    def test_quantities_known_for_every_language(self):
        for tag in re.findall(r'new Lang\("([^"]+)"', (APP / 'main/java/dev/nxnative/android/Languages.java').read_text(encoding='utf-8')):
            self.assertIn(tag.replace('-', '-r') if tag != 'en' else 'en', X.QUANTITIES)


if __name__ == '__main__':
    unittest.main()
