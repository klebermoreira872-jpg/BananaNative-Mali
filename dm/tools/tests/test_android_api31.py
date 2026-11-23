"""The launcher keeps running on Android 12 (API 31/32) when built with -PnxMinSdk=31 (internal android12 note): no Java call that exists only from API 33.

A source scan that needs no SDK, for the calls that crashed there (NoSuchMethodError) or that need a guard; the complete check is
`./gradlew -PnxMinSdk=31 -PnxPackEngine=fake lintDebug` with 0 NewApi in build/reports/lint-results-debug.xml (docs/agents/06-dev-loop.md).
A line with a `SDK_INT` check on it or within the three lines before passes; Streams.java is where the stream helpers live."""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / 'android/app/src'
# (pattern, what to use instead)
BAD = [
    (re.compile(r'(?<!Files)\.(readAllBytes|readNBytes)\s*\('), 'Streams.readAll / Streams.readUpTo (InputStream.readAllBytes is API 33 on Android)'),
    (re.compile(r'getParcelable(Extra)?\([^;]*\.class\)|getSerializable(Extra)?\([^;]*\.class\)|getParcelableArrayListExtra\([^;]*\.class\)'), 'the untyped call below API 33'),
    (re.compile(r'RECEIVER_NOT_EXPORTED|RECEIVER_EXPORTED'), 'registerReceiver without the flag below API 33'),
    (re.compile(r'\bLocaleManager\b'), 'a guard: no per-app language below API 33'),
    (re.compile(r'\bVibrationAttributes\b'), 'a guard: API 33'),
    (re.compile(r'POST_NOTIFICATIONS'), 'a guard: the permission exists from API 33'),
    (re.compile(r'PackageInfoFlags|ResolveInfoFlags|ApplicationInfoFlags'), 'the int-flag overload below API 33'),
]


class Api31(unittest.TestCase):
    def test_no_unguarded_api33_calls(self):
        bad = []
        for f in sorted(SRC.glob('*/java/**/*.java')):
            if 'jvmtest' in f.parts or f.name == 'Streams.java':
                continue
            lines = f.read_text(encoding='utf-8').splitlines()
            for n, line in enumerate(lines, 1):
                code = line.split('//')[0]
                if code.lstrip().startswith(('*', '/*', 'import ')) or any('SDK_INT' in l for l in lines[max(0, n - 4):n]):
                    continue   # a comment, an import, or a version check on this line or the three before
                for rx, use in BAD:
                    if rx.search(code):
                        bad.append(f'{f.relative_to(SRC)}:{n}: use {use}')
        self.assertEqual(bad, [], '\n'.join(bad))

    def test_default_min_sdk_stays_33(self):
        s = (SRC / '../build.gradle').resolve().read_text(encoding='utf-8')
        self.assertIn("getOrElse('33')", s)
        self.assertIn('minSdk nxMinSdk', s)


if __name__ == '__main__':
    unittest.main()
