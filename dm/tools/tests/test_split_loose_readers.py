"""Five faults of the shader split that reading it found (docs/reference/shaders.md "Shaders in a loose file that only an archive's reader was reached for" and the
entries after it): a loose file scan_blob reads was left out by the test in front of it, two readers never ended on a length of 0, a pak file's label had '\\' on
Windows, adrp_targets found no page before the adrp, and bahs_shaders stopped one entry short of the code region. Synthetic bytes only."""
import contextlib
import io
import struct
import tempfile
import threading
import unittest
import zlib
from pathlib import Path

from dm.tools.tests.test_split_gzip import fz, ss
from dm.tools.tests.test_split_viper import nvn2_stage


def scan(data, name):
    """scan_file's result for a loose RomFS file of these bytes"""
    with tempfile.TemporaryDirectory() as t, contextlib.redirect_stdout(io.StringIO()):
        path = Path(t) / 'source'; path.write_bytes(data)
        return ss.scan_file((str(path), name))


def ends(fn, *args, seconds=20):
    """fn(*args)'s SystemExit message, its result, or 'still running' after the time a reader that does not end is given"""
    got = {}
    def run():
        try: got['v'] = fn(*args)
        except SystemExit as e: got['v'] = str(e)
    t = threading.Thread(target=run, daemon=True); t.start(); t.join(seconds)
    return got.get('v', 'still running')


class LooseFiles(unittest.TestCase):
    def test_sead_primitive_drawer(self):   # four offsets, two NVN2 control sections, two code areas: no reader's magic
        (vc, vk), (pc, pk) = nvn2_stage(0x0461), nvn2_stage(0x1462)
        offs = [0x10, 0x10 + len(vc), 0x10 + len(vc) + len(pc), 0x10 + len(vc) + len(pc) + len(vk)]
        _, keys, _, extra = scan(struct.pack('<4I', *offs) + vc + pc + vk + pk, 'Lib/sead/primitive_renderer/primitive_drawer_nvn2_shader.bin')
        self.assertEqual(sorted(v[1] for v in keys.values()), ['ps', 'vs']); self.assertEqual(extra, {})

    def test_platinum_shader_object(self):   # 'VSO\0', the lengths and offsets, the control section, the code area
        ctl, code = fz.VS
        _, keys, _, _ = scan(b'VSO\0' + bytes(4) + struct.pack('<4I', len(ctl), 0x18, len(code), 0x18 + len(ctl)) + ctl + code, 'shader/a.vso')
        self.assertEqual([v[1] for v in keys.values()], ['vs'])

    def test_no_control_section_is_not_searched(self):
        self.assertFalse(ss.may_hold_shaders(b'RIFF' + bytes(0x1000)))
        self.assertEqual(scan(b'RIFF' + bytes(0x1000), 'sound/a.wav')[1:], ({}, set(), {}))

    def test_packed_containers_and_reader_magics_pass(self):   # their members' control sections are not in the file's own bytes
        for d in (b'SARC' + bytes(0x20) + b'Yaz0', b'NARC' + bytes(8), ss.PACX4 + bytes(8), ss.SUMO_MUX + bytes(8), b'XNB' + bytes(8) + ss.MGFX):
            self.assertTrue(ss.may_hold_shaders(d), d[:8])


class ZeroLengths(unittest.TestCase):
    def test_idrk_entry_of_no_length(self):
        d = ss.IDRK + struct.pack('<QQQ', 0, 0, 0) + bytes(0x40)
        self.assertIn('IDRK entry at 0x0', ends(lambda: list(ss.idrk_entries(d))))

    def test_idrk_stored_data_longer_than_the_entry(self):
        d = ss.IDRK + struct.pack('<QQQ', 0x40, 0x20, 0) + bytes(0x40)
        self.assertIn('IDRK entry at 0x0', ends(lambda: list(ss.idrk_entries(d))))

    def test_idrk_entries_read_as_before(self):
        e = ss.IDRK + struct.pack('<QQQ', 0x38, 8, 8) + bytes(0xc) + struct.pack('<I', 0) + b'_S2Gdata'
        self.assertEqual(list(ss.idrk_entries(e + e)), [(0x30, 0x38, 0, 8), (0x68, 0x70, 0, 8)])

    def test_snvn_control_section_of_no_length(self):
        ctl = bytearray(0x840); ctl[:4] = ss.CTL_MAGIC   # +0x20 (its own length) and +0x704 are 0
        z = zlib.compress(bytes(ctl))
        d = bytes(13) + struct.pack('>IIBI', 0, len(ctl), 0, len(z)) + z
        self.assertIn('says it is 0x0 bytes', ends(ss.snvn_records, d, 0, len(d), 'x'))

    def test_snvn_record_reads_as_before(self):
        ctl, code = fz.VS
        z = zlib.compress(code + ctl + bytes(0x40 - len(ctl) % 0x40 if len(ctl) % 0x40 else 0))
        d = bytes(13) + struct.pack('>IIBI', len(code), len(ctl), 0, len(z)) + z
        self.assertEqual(ss.snvn_records(d, 0, len(d), 'x'), [(26, [(ctl, code)])])


class PakPaths(unittest.TestCase):
    def test_slashes_on_every_system(self):
        self.assertEqual(ss.pak_path('../../../', 'Majesty/Content/Mat/M_A.uexp'), '../../../Majesty/Content/Mat/M_A.uexp')
        self.assertEqual(ss.pak_path('../../../Majesty/', './Content//M_A.uexp'), '../../../Majesty/Content/M_A.uexp')


class AdrpTargets(unittest.TestCase):
    def image(self, pc, target):
        img = bytearray(0x201000); imm = (((target & ~0xfff) - (pc & ~0xfff)) >> 12) & 0x1fffff
        struct.pack_into('<II', img, pc, 0x90000001 | (imm & 3) << 29 | (imm >> 2) << 5, 0x91000021 | (target & 0xfff) << 10)   # adrp x1; add x1, x1, #
        return bytes(img)

    def test_page_after_the_adrp(self):
        self.assertEqual(dict(ss.adrp_targets(self.image(0x1000, 0x200010), 0x200000, 0x201000)), {0x200010: [0x1004]})

    def test_page_before_the_adrp(self):
        self.assertEqual(dict(ss.adrp_targets(self.image(0x200000, 0x1010), 0, 0x2000)), {0x1010: [0x200004]})


class BahsLastEntry(unittest.TestCase):
    def test_entry_right_before_the_code_region(self):
        ctl, code = fz.VS; at, region = 0x20, 0x20 + len(ctl) + 16   # header, the control section, one entry, the code region
        d = bytearray(b'BAHS' + bytes(0x1c)); struct.pack_into('<II', d, 0x18, len(code), region)
        d += ctl + struct.pack('<IIIi', 0, 0, len(ctl), at - (region - 16)) + code
        self.assertEqual([(w, st) for w, st, _, _ in ss.bahs_shaders(bytes(d), 'x')], [(f'x#BAHS@{region - 16:#x}', 'vs')])


if __name__ == '__main__':
    unittest.main()
