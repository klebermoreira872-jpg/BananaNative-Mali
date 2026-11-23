"""Prepare without shaders (a game the shader layer covers, android/SHADERS.md "Prepare without shaders"): scripts/pack_android.py --optional-shaders packs a current
library when the cache has one and otherwise packs without, with no error and nothing built; the phone's pack step of a code-only job (Job.codeOnly) passes it; its shaders step
(a later job the player starts) lets the delta take entries of the library the run-time layer built (<pack>/shaders/layer/lib); a pack zip without a library imports."""
import argparse
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
import pack_android   # noqa: E402
import game           # noqa: E402

OD = REPO / 'android/app/src/ondevice/java/dev/nxnative/android'
MAIN = REPO / 'android/app/src/main/java/dev/nxnative/android'


class OptionalShaders(unittest.TestCase):
    def args(self, d, **kw):
        return argparse.Namespace(shader_cache=Path(d), no_shaders=False, optional_shaders=True, in_process=True, **kw)

    def test_no_library_is_no_error(self):
        g = game.load('040074A01BF12000')
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.assertIsNone(pack_android.pack_shaders(self.args(d), g, d, d / 'out', d))
            self.assertFalse((d / 'out/shaders').exists(), 'nothing is made in the pack')

    def test_without_the_option_a_missing_library_still_stops_the_in_process_packer(self):
        g = game.load('040074A01BF12000')
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            a = self.args(d); a.optional_shaders = False
            with self.assertRaises(pack_android.Error): pack_android.pack_shaders(a, g, d, d / 'out', d)

    def test_option_exists(self):
        text = (REPO / 'scripts/pack_android.py').read_text(encoding='utf-8')
        self.assertIn("'--optional-shaders'", text)
        self.assertIn("'--no-shaders'", text)


class Wiring(unittest.TestCase):
    def test_pack_step_of_a_code_only_job_passes_the_option(self):
        s = (OD / 'PackService.java').read_text(encoding='utf-8')
        self.assertIn('if (j.codeOnly())', s)
        self.assertIn('"--optional-shaders"', s)

    def test_delta_takes_the_layer_library_too(self):
        s = (OD / 'PackService.java').read_text(encoding='utf-8')
        line = next(l for l in s.splitlines() if 'DMSH_VK_DELTA_FROM' in l and 'setenv' in l)
        self.assertIn('File.pathSeparator', line)
        self.assertIn('shaders/layer/lib', line)

    def test_a_code_only_job_has_no_shader_chain_and_needs_no_library(self):
        s = (OD / 'Job.java').read_text(encoding='utf-8')
        self.assertIn('if (codeOnly()) return false;', s)   # apkChanged
        self.assertIn('codeOnly() || Outputs.libraryComplete', s)   # dropMissing

    def test_pack_zip_does_not_need_a_library(self):
        s = (MAIN / 'PackZip.java').read_text(encoding='utf-8')
        self.assertNotIn('has no shader library', s)

    def test_dialog_texts(self):
        s = (MAIN / 'PrepareText.java').read_text(encoding='utf-8')
        self.assertIn('Also build all shaders now', s)
        self.assertIn('Recommended: build all shaders now for smoother play', s)
        self.assertIn('You can play now; missing shaders are built as you play.', s)


if __name__ == '__main__':
    unittest.main()
