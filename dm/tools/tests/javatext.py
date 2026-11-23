"""The launcher's Java source as the source-check tests read it.

The launcher's text lives in res/values/strings.xml and the code asks for it with Tx.s(R.string.key) (android/README.md, Languages). A test that looks for a
row's English title, a dialog's words or a label array imports this module: reading a Java file of the launcher then returns the source with each
Tx.s(R.string.key) shown as its English text ("..." in the source) and each Tx.arr(R.array.name) as new String[] {...}. Nothing else changes. Opt in with install() / uninstall() (setUpModule / tearDownModule).
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
APP = REPO / 'android/app/src'
XML = APP / 'main/res/values/strings.xml'


def _unescape(x):
    x = x.strip()
    if len(x) > 1 and x[0] == '"' and x[-1] == '"':
        x = x[1:-1]
    x = x.replace("\\'", "'").replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return x.replace('"', '\\"')


def english():
    """key -> English text (as Java source), arrays name -> list"""
    xml = XML.read_text(encoding='utf-8')
    strings = {k: _unescape(v) for k, v in re.findall(r'<string name="([A-Za-z0-9_]+)"[^>]*>(.*?)</string>', xml, re.S)}
    arrays = {k: [_unescape(i) for i in re.findall(r'<item>(.*?)</item>', body, re.S)] for k, body in re.findall(r'<string-array name="([A-Za-z0-9_]+)">(.*?)</string-array>', xml, re.S)}
    return strings, arrays


def inline(src):
    strings, arrays = english()
    src = re.sub(r'Tx\.s\((?:dev\.nxnative\.android\.)?R\.string\.(\w+)\)', lambda m: '"' + strings.get(m.group(1), m.group(1)) + '"', src)
    src = re.sub(r'Tx\.s\((?:dev\.nxnative\.android\.)?R\.string\.(\w+),', lambda m: 'Tx.s("' + strings.get(m.group(1), m.group(1)) + '",', src)
    src = re.sub(r'Tx\.arr\((?:dev\.nxnative\.android\.)?R\.array\.(\w+)\)', lambda m: 'new String[] {' + ', '.join('"' + i + '"' for i in arrays.get(m.group(1), [])) + '}', src)
    return src


_read_text = Path.read_text


def _read(self, *a, **k):
    text = _read_text(self, *a, **k)
    p = str(self)
    if p.endswith('.java') and (str(APP / 'main/java') in p or str(APP / 'ondevice/java') in p):
        return inline(text)
    return text


def install():
    """Makes Path.read_text show the English of the launcher's Java source; a test module calls it in setUpModule and uninstall() in tearDownModule,
    so tests that read the raw source (ui_strings, the pad panel's R.array check) do not depend on the order the modules run in"""
    Path.read_text = _read


def uninstall():
    Path.read_text = _read_text
