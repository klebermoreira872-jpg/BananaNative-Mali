#!/usr/bin/env python3
"""Reads and writes the launcher's string resources (android/README.md, Languages): the English source res/values/strings.xml and a translation
res/values-<lang>/strings.xml, as plain data, so a translation can be made, checked and written back without hand-editing XML.

    python3 dm/tools/i18n_xml.py export > en.json            English: {"strings": {key: text}, "plurals": {key: {quantity: text}}, "arrays": {name: [text]}}
    python3 dm/tools/i18n_xml.py write <lang> <file.json>    writes res/values-<lang>/strings.xml from a translation of that shape (same keys, same placeholders)
    python3 dm/tools/i18n_xml.py check                       every values-<lang> has the keys and the placeholders of the English; exit 1 if not

The text in the data is the real text (a newline is a newline, an apostrophe an apostrophe); the XML escaping is done here.
"""
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[2]
RES = REPO / 'android/app/src/main/res'
EN = RES / 'values/strings.xml'

# the plural forms each language needs (CLDR), in the order Android lists them
QUANTITIES = {'en': ['one', 'other'], 'es': ['one', 'many', 'other'], 'fr': ['one', 'many', 'other'], 'pl': ['one', 'few', 'many', 'other'],
              'tr': ['one', 'other'], 'zh-rCN': ['other'], 'zh-rTW': ['other'], 'ar': ['zero', 'one', 'two', 'few', 'many', 'other'],
              'ko': ['other'], 'uk': ['one', 'few', 'many', 'other'], 'de': ['one', 'other'], 'it': ['one', 'many', 'other']}
HEADER = '<!-- machine translated, unreviewed: the English res/values/strings.xml is the source; see android/README.md, Languages -->'


def unescape(x):
    x = x.strip()
    if len(x) > 1 and x[0] == '"' and x[-1] == '"':
        x = x[1:-1]
    x = re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == 'u' and len(m.group(1)) == 5 else {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), x)
    return x.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


def esc(t):
    s = escape(t).replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"').replace("'", "\\'")
    if s[:1] in '@?':
        s = '\\' + s
    if t != t.strip() or '  ' in t:
        s = '"' + s.replace("\\'", "'") + '"'
    return s


def parse(path):
    xml = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
    strings = {k: unescape(v) for k, a, v in re.findall(r'<string name="([A-Za-z0-9_]+)"([^>]*)>(.*?)</string>', xml, re.S) if 'translatable="false"' not in a}
    plurals = {k: {q: unescape(t) for q, t in re.findall(r'<item quantity="(\w+)">(.*?)</item>', body, re.S)} for k, body in re.findall(r'<plurals name="([A-Za-z0-9_]+)">(.*?)</plurals>', xml, re.S)}
    arrays = {k: [unescape(i) for i in re.findall(r'<item>(.*?)</item>', body, re.S)] for k, body in re.findall(r'<string-array name="([A-Za-z0-9_]+)">(.*?)</string-array>', xml, re.S)}
    return {'strings': strings, 'plurals': plurals, 'arrays': arrays}


def holes(t):
    """The placeholders of a text, sorted: %1$s, %2$d, %%"""
    return sorted(re.findall(r'%(?:\d+\$)?[sd%]', t))


def problems(lang, data, en):
    out = []
    for kind in ('strings', 'plurals', 'arrays'):
        miss = sorted(set(en[kind]) - set(data[kind])); extra = sorted(set(data[kind]) - set(en[kind]))
        if miss: out.append(f'{lang}: {kind} missing {miss[:5]}{"..." if len(miss) > 5 else ""} ({len(miss)})')
        if extra: out.append(f'{lang}: {kind} not in English {extra[:5]}')
    for k, t in en['strings'].items():
        if k in data['strings'] and holes(t) != holes(data['strings'][k]):
            out.append(f'{lang}: {k}: placeholders {holes(t)} became {holes(data["strings"][k])}')
    for k, forms in en['plurals'].items():
        got = data['plurals'].get(k, {})
        q = QUANTITIES.get(lang, ['one', 'other'])
        if sorted(got) != sorted(q): out.append(f'{lang}: {k}: plural forms {sorted(got)} need {sorted(q)}')
        for qq, t in got.items():
            if holes(forms['other']) != holes(t): out.append(f'{lang}: {k}[{qq}]: placeholders differ')
    for k, items in en['arrays'].items():
        if k in data['arrays'] and len(items) != len(data['arrays'][k]): out.append(f'{lang}: {k}: {len(data["arrays"][k])} items, English has {len(items)}')
    return out


def write(lang, data):
    en_xml = EN.read_text(encoding='utf-8')
    lines = ['<?xml version="1.0" encoding="utf-8"?>', HEADER, '<resources>']
    for m in re.finditer(r'<string name="([A-Za-z0-9_]+)"[^>]*>|<plurals name="([A-Za-z0-9_]+)">|<string-array name="([A-Za-z0-9_]+)">', re.sub(r'<!--.*?-->', '', en_xml, flags=re.S)):
        k, p, a = m.groups()
        if k and k in data['strings']:
            lines.append(f'    <string name="{k}">{esc(data["strings"][k])}</string>')
        elif p and p in data['plurals']:
            lines.append(f'    <plurals name="{p}">')
            for q in QUANTITIES.get(lang, ['one', 'other']):
                lines.append(f'        <item quantity="{q}">{esc(data["plurals"][p][q])}</item>')
            lines.append('    </plurals>')
        elif a and a in data['arrays']:
            lines.append(f'    <string-array name="{a}">')
            lines += [f'        <item>{esc(i)}</item>' for i in data['arrays'][a]]
            lines.append('    </string-array>')
    lines.append('</resources>')
    d = RES / f'values-{lang}'
    d.mkdir(exist_ok=True)
    (d / 'strings.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv):
    en = parse(EN)
    if argv[:1] == ['export']:
        json.dump(en, sys.stdout, ensure_ascii=False, indent=1)
        return 0
    if argv[:1] == ['write']:
        lang, f = argv[1], argv[2]
        data = json.load(open(f, encoding='utf-8'))
        bad = problems(lang, data, en)
        for b in bad: print(b)
        if bad: return 1
        write(lang, data)
        return 0
    if argv[:1] == ['check']:
        bad = []
        for d in sorted(RES.glob('values-*')):
            f = d / 'strings.xml'
            if f.exists() and d.name[7:] in QUANTITIES:
                bad += problems(d.name[7:], parse(f), en)
        for b in bad: print(b)
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
