#!/usr/bin/env python3
"""Inventory of the launcher's hard-coded user-visible strings (android/README.md, Languages).

Scans android/app/src/main/java and android/app/src/ondevice for string literals passed to the UI calls the launcher draws its text with:
Ui.text/section/heading/body/small/button/action/status/tag/chip, new Ui.Setting(...), .value/.says/.badge/.note/.status/.tag,
setTitle/setMessage/setPositiveButton/setNegativeButton/setNeutralButton, Toast.makeText, setContentDescription, setText/setHint,
setItems/setSingleChoiceItems, Ui.explain/sheet/confirmDanger/header, error(...) and the labels of String[] arrays.
Text that comes from resources (getString, R.string) is not a literal and is not counted.

    python3 dm/tools/ui_strings.py            counts per file
    python3 dm/tools/ui_strings.py --list     every literal with file and line
    python3 dm/tools/ui_strings.py --check    exit 1 for a literal that is neither moved to resources nor in dm/tools/ui_strings_allow.txt

The allow-list holds the literals that stay English on purpose (Advanced switch names, log text, env names). One line each: "<file>\t<literal>"
(the literal as in the source, escapes kept); '#' starts a comment. A literal is matched by file and text, not by line.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOTS = [REPO / 'android/app/src/main/java', REPO / 'android/app/src/ondevice']
ALLOW = Path(__file__).with_name('ui_strings_allow.txt')

CALLS = ('Ui.text', 'Ui.section', 'Ui.heading', 'Ui.body', 'Ui.small', 'Ui.button', 'Ui.action', 'Ui.status', 'Ui.tag', 'Ui.chip',
         'new Ui.Setting', 'new Problem', '.value', '.says', '.badge', '.note', '.status', '.tag',
         'setTitle', 'setMessage', 'setPositiveButton', 'setNegativeButton', 'setNeutralButton', 'Toast.makeText',
         'setContentDescription', 'setText', 'setHint', 'setItems', 'setSingleChoiceItems', 'setMultiChoiceItems',
         'Ui.explain', 'Ui.sheet', 'Ui.confirmDanger', 'Ui.header', 'Ui.iconButton', 'Ui.more', 'Ui.navItem', 'Ui.chip', 'error', 'pickFolder',
         'head', 'note', 'title', 'sharpTitle', 'Ui.warnChip', 'Ui.statusChip', 'Ui.sectionHeader', 'Ui.tile', 'Ui.details', 'radio', 'choose', 'ownChoice')
# A dotted call (row.value(...), hold.says(...)) counts on any receiver but the log's (Native.note, Log.i ...); the others must not follow a word.
# head(...) / note(...) are the in-game panel's row helpers; Words.s is the pure classes' text (its English is the fallback of the key, checked against strings.xml)
NOT_UI = ('Native', 'Log', 'Json', 'Pattern', 'String', 'Integer', 'Boolean', 'Objects', 'Arrays', 'Collections', 'Files', 'Math')
_DOT = sorted((c for c in CALLS if c.startswith('.')), key=len, reverse=True)
_PLAIN = sorted((c for c in CALLS if not c.startswith('.')), key=len, reverse=True)
CALL_RE = re.compile(r'(?<![\w$])(?<!Native\.)(?<!Log\.)(?<!Json\.)(' + '|'.join(re.escape(c) for c in _PLAIN) + r')\s*\('
                     r'|(?<![\w$])(?!(?:' + '|'.join(NOT_UI) + r')\b)[\w$\]\)]+(' + '|'.join(re.escape(c) for c in _DOT) + r')\s*\(')
ARRAY_RE = re.compile(r'String\[\]\s*(?:\w+\s*=\s*)?(?:new\s+String\[\]\s*)?\{')
LIT_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def mask_comments(src):
    """The source with comments blanked (same length), so a quote in a comment is not read; string literals are kept."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1]); i = j + 1
        elif c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1]); i = j + 1
        elif src.startswith('//', i):
            j = src.find('\n', i); j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2); j = n if j < 0 else j + 2
            out.append(''.join(ch if ch == '\n' else ' ' for ch in src[i:j])); i = j
        else:
            out.append(c); i += 1
    return ''.join(out)


def balanced(src, open_at):
    """Index after the parenthesis that closes the one at open_at (strings and char literals skipped)."""
    depth, i, n = 0, open_at, len(src)
    while i < n:
        c = src[i]
        if c in '"\'':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            i = j
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def is_text(lit):
    """True for a literal that reads as words for the player: has two letters in a row and is not a key, a path, a format-only or an env-like token."""
    if not re.search(r'[A-Za-z]{2}', lit):
        return False
    if re.fullmatch(r'[A-Za-z0-9_.:/\\%$#-]+', lit) and not re.search(r'[A-Z][a-z]+$', lit) :
        return False   # one token: a key, a file name, a package, an env name
    return True


# The second tier: in the classes that draw the launcher's screens, any literal of three words or more is text for the player (a switch label, a sentence built
# with append or +, a ternary's branch) unless it sits in a log call, an exception, a comparison or a key. Words.s / Tx.s texts are not literals of the code.
SENTENCE_CLASSES = ('MainActivity', 'GameSettings', 'SidePanel', 'Overlay', 'TouchControls', 'Ui', 'StepSlider', 'DrsSlider', 'GameUpscaler', 'DlssTune', 'StorageUi', 'SaveUi',
                    'PackUi', 'Folders', 'CheatsUi', 'Lsfg', 'LinkPlay', 'PadMapUi', 'UsersUi', 'CtrlScreen', 'GpuDriver', 'Ondevice', 'Prefs', 'ReadinessActivity', 'GameActivity',
                    'Updater', 'ReleasePage', 'DriverFetch', 'FrontendLaunch', 'PrepareText', 'Readiness', 'LayerStatus', 'ShaderState', 'BuildCheck', 'Job', 'StorageScan',
                    'ExitNotice', 'ExitWatch', 'Profile', 'Recommend', 'PackService', 'GameCopy', 'FixOffer', 'SelftestActivity', 'TimeOfDay', 'Shortcuts', 'UserPicker', 'TextInput')
QUIET = re.compile(r'(Native\.\w+\(|Log\.[a-z]\(|Exception\(|Error\(|\.put\w*\(|getString\(|\.equals\(|equalsIgnoreCase\(|startsWith\(|endsWith\(|contains\(|\.has\(|opt\w*\(|gameKey\(|Pattern|\.split\(|\.replace\w*\(|case |indexOf\(|matches\(|System\.|getExtra|putExtra|setAction|Uri\.|File\(|ClipData|\.note\("\[|Json|BuildConfig)')


def inside_words(before):
    """True when the position after `before` is inside the arguments of a Words.s / Words.n / Tx.s call (the English fallback, the key)"""
    for m in re.finditer(r'(?:Words\.[sn]|Tx\.[sn])\(', before):
        depth, i, q = 1, m.end(), False
        while i < len(before):
            c = before[i]
            if c == '"' and before[i - 1] != '\\':
                q = not q
            elif not q and c == '(':
                depth += 1
            elif not q and c == ')':
                depth -= 1
            if depth == 0:
                break
            i += 1
        if depth > 0:
            return True
    return False


def sentences(path):
    if path.stem not in SENTENCE_CLASSES:
        return []
    src = mask_comments(open(path, encoding='utf-8').read())
    out = []
    for m in LIT_RE.finditer(src):
        lit = m.group(1)
        if len(re.findall(r'[A-Za-z]{2,}', lit)) < 3 or lit.count(' ') < 2 or re.search(r'^[A-Z_]+=|DM_|^\[|%[.,]?\d*[a-z]', lit):
            continue
        ls = src.rfind('\n', 0, m.start()) + 1
        if QUIET.search(src[ls:m.start()][-60:]) or inside_words(src[ls:m.start()]):
            continue   # (Words.s("key", "English"): the English is the key's fallback, checked against strings.xml)
        out.append((src.count('\n', 0, m.start()) + 1, lit))
    return out


def scan(path):
    src = mask_comments(open(path, encoding='utf-8').read())   # raw: a test that imported javatext has patched Path.read_text
    found = []
    for m in CALL_RE.finditer(src):
        start = m.end() - 1
        end = balanced(src, start)
        body = src[start:end]
        # literals inside a nested lambda block belong to calls of their own, found separately; here only literals outside braces
        depth, cur = 0, []
        for i, ch in enumerate(body):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        for lm in LIT_RE.finditer(body):
            before = body[:lm.start()]
            if before.count('{') - before.count('}') > 0:
                continue
            if is_text(lm.group(1)):
                line = src.count('\n', 0, start + lm.start()) + 1
                found.append((line, lm.group(1)))
    for m in ARRAY_RE.finditer(src):
        start = m.end() - 1
        depth, i = 0, start
        while i < len(src):
            if src[i] == '{': depth += 1
            elif src[i] == '}':
                depth -= 1
                if depth == 0: break
            elif src[i] == '"':
                i += 1
                while src[i] != '"': i += 2 if src[i] == '\\' else 1
            i += 1
        for lm in LIT_RE.finditer(src[start:i]):
            if is_text(lm.group(1)):
                found.append((src.count('\n', 0, start + lm.start()) + 1, lm.group(1)))
    found += sentences(path)
    # the same literal reached by two calls on one line (Ui.text inside Ui.add ...) counts once
    return sorted(set(found))


def inventory():
    res = {}
    for root in ROOTS:
        for p in sorted(root.rglob('*.java')):
            hits = scan(p)
            if hits:
                res[str(p.relative_to(REPO / 'android/app/src'))] = hits
    return res


def allow():
    out = set()
    if ALLOW.exists():
        for ln in ALLOW.read_text(encoding='utf-8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                f, _, lit = ln.partition('\t')
                out.add((f, lit))
    return out


def violations():
    ok = allow()
    return [(f, ln, lit) for f, hits in inventory().items() for ln, lit in hits if (f, lit) not in ok]


def main(argv):
    inv = inventory()
    if '--check' in argv:
        bad = violations()
        for f, ln, lit in bad:
            print(f'{f}:{ln}: hard-coded UI text "{lit}" (use a string resource, or add it to dm/tools/ui_strings_allow.txt)')
        return 1 if bad else 0
    if '--list' in argv:
        for f, hits in inv.items():
            for ln, lit in hits:
                print(f'{f}:{ln}\t{lit}')
    total = 0
    for f, hits in sorted(inv.items(), key=lambda kv: -len(kv[1])):
        print(f'{len(hits):5d}  {f}'); total += len(hits)
    print(f'{total:5d}  total in {len(inv)} files')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
