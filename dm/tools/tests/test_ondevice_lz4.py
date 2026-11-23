#!/usr/bin/env python3
"""The on-device packer's Python (android/ondevice/build.sh) carries every python-lz4 submodule the tools it runs import.

build.sh builds lz4 and lz4.block only. A tool that imports another submodule (lz4.frame) works on a computer and fails on the phone, where the import is
missing: the .cmp containers of Kirby and the Forgotten Land's add-on stayed closed that way until shader_split.py decoded LZ4 frames with lz4.block
(lz4_frame, BananaNative #356), and Kirby's Return to Dream Land Deluxe's ptcl/ containers did in Peanuts Native. Either the tool keeps to the submodules
build.sh builds, or build.sh builds the one it imports."""
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TOOL_DIRS = ['scripts', 'dm/tools', 'dm/games', 'dm/gfx/tools']   # the tool folders the APK's tools.zip carries (android/app/build.gradle nxPackTools)


def imported_lz4_submodules():
    found = {}
    pat = re.compile(r'^\s*(?:import\s+lz4\.(\w+)|from\s+lz4\.(\w+)\s+import|from\s+lz4\s+import\s+(\w+))', re.M)
    for d in TOOL_DIRS:
        top = os.path.join(ROOT, d)
        for name in sorted(os.listdir(top)):
            if not name.endswith('.py'): continue
            with open(os.path.join(top, name), encoding='utf-8') as f: src = f.read()
            for m in pat.finditer(src):
                found.setdefault(next(g for g in m.groups() if g), f'{d}/{name}')
    return found


class OndeviceLz4(unittest.TestCase):
    def test_every_imported_submodule_is_built(self):
        with open(os.path.join(ROOT, 'android/ondevice/build.sh'), encoding='utf-8') as f: sh = f.read()
        subs = imported_lz4_submodules()
        self.assertIn('block', subs)   # the rewriter's NSO reader and shader_split.py: the scan itself must keep finding imports
        for sub, where in subs.items():
            self.assertTrue(re.search(rf'-o \$SP/lz4/{sub}/_{sub}\.\$SFX ', sh), f'{where} imports lz4.{sub}, which build.sh does not build for the phone')
            self.assertTrue(re.search(rf'cp \$L/lz4/{sub}/\S*\.py \$SP/lz4/{sub}/', sh), f'build.sh does not copy lz4.{sub}\'s Python files')


if __name__ == '__main__':
    unittest.main()
