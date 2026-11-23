"""The launcher's shader states (android/SHADERS.md "Launcher states for shaders"): why the shader layer does not let a game with no library play now (ShaderState.layerOff),
the "Shaders needed" words with the player's way forward for each cause (ShaderState.neededText), the layer's folder check (ShaderLibs.layerWritable: no folder, no layer, so the
game is not treated as one that builds its shaders as it plays), and Import a library's check of a picked dmsh_vk.lib (ShaderLibs.importProblem), on the JVM with
android/app/src/jvmtest's ShaderStateJvmTest; and the wiring of the fixes in the launcher's sources. No game files; the JVM part is skipped without a JDK."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # the tests folder, for javatext (unittest by file name does not add it)
import javatext  # noqa: E402
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WORDS = REPO / 'android/app/src/main/java/dev/nxnative/android/Words.java'   # the pure classes' text (Words), compiled with them
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / 'dm/gfx/tools'))
import vk_android_delta as delta   # noqa: E402
from test_android_shader_delta import spirv, write_lib   # noqa: E402

J = REPO / 'android/app/src'
MAIN = J / 'main/java/dev/nxnative/android'
SRC = [MAIN / f'{n}.java' for n in ('ShaderState', 'ShaderLibs')]
TEST = J / 'jvmtest/java/dev/nxnative/android/ShaderStateJvmTest.java'
GAME = '040074A01BF12000'


def read(p): return p.read_text(encoding='utf-8')


class Wiring(unittest.TestCase):
    def test_launcher_uses_the_states(self):
        ma, gs, pack, pu = read(MAIN / 'MainActivity.java'), read(MAIN / 'GameSettings.java'), read(MAIN / 'Pack.java'), read(MAIN / 'PackUi.java')
        od = read(J / 'ondevice/java/dev/nxnative/android/Ondevice.java')
        # (1) a covered game whose switch is off: the card's Why? names the switch, Play offers to turn it on, the page shows the switch in its Shaders needed row
        self.assertIn('GameSettings.neededText(pd, g.titleId, s.off, dump)', ma)
        self.assertIn('"Turn on and play"', ma)
        self.assertIn('shadersNeededRow(a, content, g, again)', gs)
        self.assertIn('off == ShaderState.Off.SWITCH', gs)
        # (4) no folder the layer can be built in: not on demand
        self.assertIn('ShaderLibs.layerWritable(dir, ShaderLibs.tempOf(titleId))', pack)
        self.assertIn('ShaderLibs.appFiles = getExternalFilesDir(null)', read(MAIN / 'NxApp.java'))
        # a .nup picked in place has no file at its stand-in path: its page still has the shader rows
        self.assertIn('!PickedNup.is(a, g.gameDir) && !new File(g.gameDir).exists()', gs)
        # (7) the Shaders row is always there (one small row, a tap opens its dialog): the state is never hidden
        self.assertIn('shadersOnDemandRow(a, content, g, again)', gs); self.assertIn('shadersDialog(a, g, dump, again)', gs)
        # (9) Import a library is a file picker, wired to the activity result
        self.assertIn('PICK_IMPORT_LIB', pu); self.assertIn('ShaderLibs.importProblem(h, tmp.length()', pu); self.assertIn('tmp.renameTo(lib)', pu)
        self.assertIn('PackUi.documentResult(this, request, data.getData())', ma)
        self.assertNotIn('importLibraryText', read(MAIN / 'PrepareText.java'))
        # (3) a Build all that runs, waits or failed keeps Play on for a pack that plays on the layer; a whole Prepare stuck in its shaders can finish without them
        self.assertIn('playsOnLayer(j)', od); self.assertIn('skipShaders(j)', od)
        self.assertIn('canSkipShaders()', read(J / 'ondevice/java/dev/nxnative/android/Job.java'))
        # an older library the layer fills (any ABI the host plays, any inputs digest): the small row "Shaders: older, built while playing", never the big card
        self.assertIn('Pack.shaderLayerFills(new File(g.packDir)', gs); self.assertIn('Pack.shaderLayerFills(pd', gs)
        self.assertIn('static boolean shaderLayerFills(', pack); self.assertIn('ShaderLibs.layerCovers(titleId, gameEnv)', pack[pack.index('static boolean shaderLayerFills('):])
        self.assertNotIn('Shader update available', gs)
        pt = read(MAIN / 'PrepareText.java')
        self.assertIn('static String OLDER_LAYER_TITLE()', pt); self.assertIn('"Shaders: older, built while playing"', pt); self.assertIn('static String olderLayerText(boolean same, boolean dump)', pt)
        # not a dump: no card that says the update starts by itself
        self.assertIn('problem.playable && !problem.prepare', ma)

    def test_optional_shaders_wiring(self):
        """Ondevice.checked decides with ShaderState.need; a code update of a pack that plays keeps its library (code only, shaders recommended); an automatic update
        never starts a whole Prepare or a large delta, nor a job the player paused"""
        od = read(J / 'ondevice/java/dev/nxnative/android/Ondevice.java'); ma = read(MAIN / 'MainActivity.java'); pack = read(MAIN / 'Pack.java')
        checked = od[od.index('void checked(Found f'):od.index('void askPrepare(')]
        self.assertIn('ShaderState.need(onLayer, older, code, shaders)', checked)
        self.assertNotIn('Pack.libraryOf(pd) == null) {', checked, 'the old rule: code only only for a covered pack with no library')
        self.assertIn('if (start) { adopt(r, pd, true, false); return; }', checked)
        self.assertIn('PrepareText.recommendText(minutes, builds)', checked)
        self.assertIn('if (card && need == ShaderState.Need.CODE_AND_SHADERS) return;', checked)
        self.assertIn('if (card && s.equals("paused") && "user".equals(j.reason())) return;', checked)
        self.assertIn('if (!Pack.deltaAutomatic(packDir, titleId) || !autoTried.add(dump.getPath())) return;', od)
        self.assertIn('ShaderState.canSkipShaders(', od); self.assertIn('j.redoesCode()', od)
        self.assertIn('Ondevice.prepareShaders(this, new File(g.gameDir), true)', ma)
        self.assertIn('!Pack.deltaAutomatic(new File(g.packDir), g.titleId)', ma)
        self.assertIn('&& !deltaAutomatic(dir, titleId)', pack)
        self.assertIn('j.o.put("redo_code", code);', read(J / 'ondevice/java/dev/nxnative/android/Job.java'))

    def test_prepare_is_a_ring_on_the_tile(self):   # the job shows as the tile's ring in every state, its details in the sheet; no wide card in the game list
        ma, od = read(MAIN / 'MainActivity.java'), read(J / 'ondevice/java/dev/nxnative/android/Ondevice.java')
        for s in ('TILE_RUNNING', 'TILE_QUEUED', 'TILE_PAUSED', 'TILE_FAILED', 'TILE_DONE'): self.assertIn(s, od); self.assertIn(s, ma, s)
        self.assertIn('static int tileState()', od); self.assertNotIn('static View cardView()', od)
        self.assertIn('v -> Ondevice.sheet(this)', ma); self.assertIn('ti.ring.look(', ma)
        self.assertNotIn('Ondevice.cardView()', ma)
        self.assertNotIn('sampleCard', ma)

    def test_texts(self):
        """Menu paths with ›, Prepare shaders as elsewhere, no Prepare again for a game the phone cannot prepare"""
        for f in ('ShaderState.java', 'PrepareText.java', 'GameSettings.java', 'PackUi.java', 'Folders.java'):
            t = read(MAIN / f)
            self.assertNotIn('Storage \\u203a Prepare again makes the whole set', t, f)
            self.assertNotIn('. the game page', t, f)


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class Jvm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        subprocess.run(['javac', '-Xlint:all', '-Werror', '-encoding', 'UTF-8', '-d', str(cls.tmp / 'classes'), str(WORDS), *map(str, SRC), str(TEST)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def java(self, *a):
        return subprocess.run(['java', '-cp', str(self.tmp / 'classes'), 'dev.nxnative.android.ShaderStateJvmTest', *map(str, a)], check=True, capture_output=True, text=True).stdout.strip()

    def test_layer_off(self):
        self.assertEqual(self.java('off', GAME, 1, '-', 1), 'off NONE')
        self.assertEqual(self.java('off', '0100000000010000', 1, '-', 1), 'off NOT_SWITCH2', 'a Maxwell title: nothing the player can change')
        self.assertEqual(self.java('off', GAME, 0, 'DM_VK_LAYER=0', 0), 'off SWITCH', 'the switch first: the page shows it')
        self.assertEqual(self.java('off', GAME, 1, 'DM_X=1\\nDM_VK_LAYER=0', 1), 'off ENV')
        self.assertEqual(self.java('off', GAME, 1, 'DM_VK_LAYER=1', 0), 'off UNWRITABLE')

    def test_needed_text(self):
        """Every cause names what the player can do: the switch's path, the line's, the folder; then Prepare shaders for a dump, Import a library for any other file"""
        t = self.java('needed', 'SWITCH', 0, 1, -1, 22852)
        self.assertIn('Shaders while playing is off', t); self.assertIn('the game page › Performance › Advanced › Shaders while playing', t)
        self.assertIn('Prepare shaders makes them from your dump (about 9-40 minutes', t)
        t = self.java('needed', 'ENV', 0, 0, -1, 22852)
        self.assertIn('DM_VK_LAYER=0', t); self.assertIn('Extra environment', t); self.assertIn('Import a library', t); self.assertNotIn('Prepare shaders', t)
        t = self.java('needed', 'UNWRITABLE', 0, 1, -1, 100)
        self.assertIn('can be written', t); self.assertIn('Storage › Folders', t)
        t = self.java('needed', 'NOT_SWITCH2', 0, 1, 512, 22852)
        self.assertIn('translates the 512 new ones (the other 22,340 are reused', t); self.assertNotIn('Shaders while playing', t)
        t = self.java('needed', 'NOT_SWITCH2', 0, 1, 0, 22852)
        self.assertIn('none needs translating again', t); self.assertNotIn('up to date', t, 'never "up to date" on a card that says Shaders needed')
        t = self.java('needed', 'SWITCH', 1, 1, -1, 10)
        self.assertIn('other shader tables', t); self.assertNotIn('Shaders while playing', t, 'the layer cannot fill a library of this version: the switch is no way forward')
        t = self.java('needed', 'NONE', 0, 0, -1, 10)
        self.assertIn('scripts/pack_android.py', t); self.assertIn('Storage › Import pack', t)

    def test_on_demand_text(self):
        row, note = self.java('ondemand', 1).split('\t')
        self.assertIn('Build all', row); self.assertIn('Settings › Storage', row); self.assertIn('Build all', note); self.assertNotIn('Prepare again', row + note)
        row, note = self.java('ondemand', 0).split('\t')
        self.assertNotIn('Build all', row + note, 'not a dump: no Build all on its page'); self.assertIn('Import a library', row); self.assertIn('Import a library', note)
        self.assertIn('Storage \u203a Prepare again', self.java('legacy', 1)); self.assertNotIn('Prepare', self.java('legacy', 0)); self.assertIn('Import a library', self.java('legacy', 0))

    def test_need(self):
        """Shaders are the player's choice whenever the game plays without them; required only when nothing plays (no library the host plays, the layer does not cover it).
        The trigger (2026-11-21): a code update of Fire Emblem Fortune's Weave (`04007EF01F8AE000`) whose pack held only older libraries translated all 16,888 shaders"""
        n = lambda covered, older, code, shaders: self.java('need', covered, older, code, shaders)
        for c in (0, 1):
            for o in (0, 1):
                self.assertEqual(n(c, o, 0, 0), 'need NOTHING')
                self.assertEqual(n(c, o, 1, 0), 'need CODE_ONLY')
        self.assertEqual(n(1, 0, 1, 1), 'need CODE_SHADERS_OPTIONAL', 'covered, no library: code only, shaders offered')
        self.assertEqual(n(0, 1, 1, 1), 'need CODE_SHADERS_OPTIONAL', 'an older library plays: a code update keeps it (the bug)')
        self.assertEqual(n(1, 1, 1, 1), 'need CODE_SHADERS_OPTIONAL')
        self.assertEqual(n(1, 0, 0, 1), 'need SHADERS_OPTIONAL')
        self.assertEqual(n(0, 1, 0, 1), 'need SHADERS_OPTIONAL')
        self.assertEqual(n(0, 0, 1, 1), 'need CODE_AND_SHADERS', 'nothing plays: the shaders are required')
        self.assertEqual(n(0, 0, 0, 1), 'need SHADERS')

    def test_auto_delta(self):
        """A delta update starts by itself when nothing plays meanwhile (required anyway), or when it is small (a quarter of the set at most); otherwise it is an offer"""
        a = lambda d, t, p: self.java('autodelta', d, t, p)
        self.assertEqual(a(-1, 22852, 0), 'autodelta false', 'no manifest row: never by itself')
        self.assertEqual(a(-1, 22852, 1), 'autodelta false')
        self.assertEqual(a(22396, 22852, 0), 'autodelta true', 'nothing plays: as before')
        self.assertEqual(a(22396, 22852, 1), 'autodelta false', 'plays meanwhile, nearly the whole set: an offer')
        self.assertEqual(a(2322, 22852, 1), 'autodelta true', 'the 2026-11-03 translator change: small')
        self.assertEqual(a(5713, 22852, 1), 'autodelta true'); self.assertEqual(a(5714, 22852, 1), 'autodelta false')
        self.assertEqual(a(0, 22852, 1), 'autodelta true')

    def test_skip_shaders(self):
        """Finish without shaders: when the game plays without the set and the job makes something the pack lacks"""
        k = lambda c, o, r, p: self.java('skip', c, o, r, p)
        self.assertEqual(k(1, 0, 1, 0), 'skip true', 'a whole Prepare of a covered game')
        self.assertEqual(k(0, 1, 1, 1), 'skip true', 'a code update of a pack with an older library')
        self.assertEqual(k(1, 1, 0, 1), 'skip false', 'a shaders-only update of a pack that plays: just pause it')
        self.assertEqual(k(1, 0, 0, 0), 'skip true', 'covered, the pack does not play yet')
        self.assertEqual(k(0, 0, 1, 0), 'skip false', 'nothing plays without the shaders')

    def test_layer_writable(self):
        """The pack's shaders/layer, else the temporary folder's shader_layer; nothing is made by the check"""
        d = self.tmp / 'w'; pack = d / 'pack'; temp = d / 'temp/' / GAME
        pack.mkdir(parents=True)
        self.assertEqual(self.java('writable', pack, temp), 'writable true')
        self.assertFalse((pack / 'shaders').exists(), 'the check makes nothing')
        if os.geteuid() != 0:
            pack.chmod(0o555)
            try:
                self.assertEqual(self.java('writable', pack, temp), 'writable true', 'the temporary folder takes it')
                self.assertEqual(self.java('writable', pack, '-'), 'writable true', 'the temporary folder not known: the host\'s own fallback')
                d.chmod(0o555)
                try:
                    self.assertEqual(self.java('writable', pack, temp), 'writable false', 'neither can be written: the host would have no layer')
                finally:
                    d.chmod(0o755)
                (pack.parent / 'temp').mkdir(exist_ok=True)
                (pack.parent / 'temp').chmod(0o555)
                self.assertEqual(self.java('writable', pack, temp), 'writable false')
                (pack.parent / 'temp').chmod(0o755)
            finally:
                pack.chmod(0o755)
        (pack / 'shaders').write_text('a file, not a folder')
        self.assertEqual(self.java('writable', pack, temp), 'writable true', 'the temporary folder still takes it')

    def test_import_problem(self):
        d = self.tmp / 'imp'; abi = delta.abi_digest(); cur = '76b097613f15'; inp = '5dd843bed8d1'
        sh = [('00000000000000aa', [spirv(10, 1)], b'')]
        def lib(name, version, **k):
            p = d / name / 'dmsh_vk.lib'; write_lib(p, version, shaders=k.pop('shaders', sh), codec=0, **k); return p
        self.assertEqual(self.java('import', lib('own', cur, abi=abi), GAME, cur, abi, '-', inp), f'import ok v-{cur}')
        self.assertEqual(self.java('import', lib('older', '111111111111', abi=abi), GAME, cur, abi, '-', inp), 'import ok v-111111111111', 'an older version of this ABI plays')
        self.assertEqual(self.java('import', lib('compat', '674db0a4ff79', abi='674db0a4ff79'), GAME, cur, abi, '674db0a4ff79 0a0a0a0a0a0a', inp), 'import ok v-674db0a4ff79')
        self.assertIn('cannot play', self.java('import', d / 'compat/dmsh_vk.lib', GAME, cur, abi, '-', inp), 'that ABI without the compat list')
        self.assertIn('another game', self.java('import', lib('other', cur, abi=abi, game='0400000000001000'), GAME, cur, abi, '-', inp))
        self.assertIn('before versioned', self.java('import', lib('legacy', '444444444444', abi=''), GAME, cur, abi, '-', inp))
        self.assertIn('other shader tables', self.java('import', lib('inputs', cur, abi=abi, inputs='aaaaaaaaaaaa'), GAME, cur, abi, '-', inp))
        self.assertEqual(self.java('import', d / 'inputs/dmsh_vk.lib', GAME, cur, abi, '-', '-'), f'import ok v-{cur}', 'inputs not known: not refused for them')
        self.assertIn('no shaders', self.java('import', lib('empty', cur, abi=abi, shaders=()), GAME, cur, abi, '-', inp))
        whole = lib('cut', cur, abi=abi).read_bytes()
        (d / 'cut/dmsh_vk.lib').write_bytes(whole[:len(whole) - 8])
        self.assertIn('cut short', self.java('import', d / 'cut/dmsh_vk.lib', GAME, cur, abi, '-', inp))
        (d / 'junk').mkdir(); (d / 'junk/dmsh_vk.lib').write_bytes(b'PK\3\4' + bytes(200))
        self.assertIn('not a shader library', self.java('import', d / 'junk/dmsh_vk.lib', GAME, cur, abi, '-', inp))
        bad = bytearray(whole); bad[24:40] = b'v-../../x'.ljust(16, b'\0')
        (d / 'badver').mkdir(); (d / 'badver/dmsh_vk.lib').write_bytes(bytes(bad))
        self.assertIn('no version', self.java('import', d / 'badver/dmsh_vk.lib', GAME, cur, abi, '-', inp), 'the folder name comes from the header: only 12 hex digits')


def setUpModule():
    javatext.install()   # the launcher text is in strings.xml: this module reads the Java source with its English


def tearDownModule():
    javatext.uninstall()


if __name__ == '__main__':
    unittest.main()
