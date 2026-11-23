"""Pokopia 2.0.1 aspect and native 4:3 variant hooks, exact main NSO build.

Base OBS gates (28, 29, 30|0..3, 30|6..7) feed dm/host/android/pkp_aspect.c:
- Without DM_PATCH_VARIANT, DM_PKP_ASPECT / DM_VK_PICTURE_ASPECT (Screen shape) drives
  world cameras and Screen shape UI scaling/anchoring (30|1..3, 30|6..7); 30|4..5 are no-ops.
- With DM_PATCH_VARIANT=43 (and VARIANT_CUTS['43'] applied to main), world cameras run at 4:3
  with T95 portrait-camera correction on 30|0, while 30|3..5 dispatch kg175 UI rules (pkp_ui43.c)
  and 30|1..2 are no-ops.
- Gates 30|6 (0xebecec) and 30|7 (0xebedd0) adjust event mask rects for both Screen shape and variant 43.
"""
import struct


def _b(frm, to):
    off = (to - frm) // 4
    assert -(1 << 25) <= off < (1 << 25)
    return 0x14000000 | (off & 0x3FFFFFF)


def _hx(words):
    return b''.join(struct.pack('<I', w) for w in words).hex()


_main = '76a489f3bd3642fa5e18bd83d32c98ba'

OBS = {
    _main: [
        (0x08cc128, 28, '398dc273', 'scene camera enters render view; x20 camera'),
        (0x1f12130, 29, 'aa0003f3', 'projection builder entry; x0 camera'),
        (0x1f12354, 30, '6d4123e9', 'perspective projection exit; x19 camera'),
        (0x1f1230c, 30 | 1 << 8, '6d4123e9', 'orthographic projection exit (the UI 2D cameras); x19 camera'),
        (0x17b9804, 30 | 2 << 8, '52800028', '2D batch constants just stored (text in screen pixels); x8 the four words'),
        (0x1f72270, 30 | 3 << 8, 'f9401e68', 'ScreenLayout pane transform update, global matrix final, children next; x19 pane, x20 what changed'),
        (0x1f84fac, 30 | 4 << 8, 'aa1f03e3', 'ScreenLayout pre-bake before bl 0x1f85000; x0 scaleobj, x1 pane'),
        (0x1f84fb4, 30 | 5 << 8, 'f9400288', 'ScreenLayout post-bake after bl 0x1f85000; x19 scaleobj'),
        (0x0ebecec, 30 | 6 << 8, 'f9401108', 'event stencil mask quad rect before submit; x1 rect[4]'),
        (0x0ebedd0, 30 | 7 << 8, 'f9400108', 'event alpha-mask quad rect before submit; x1 rect[4], x19 entry'),
    ],
}

# Three minimal cuts for variant 43 placed in .text padding 0x2749480..0x2749504 (TEXT_END 0x2749480..RO_OFF 0x274a000):
# - fitw (0x9131a8 -> 0x2749480): scales layout root scaleobj sy to 0.75 * s (leaves so+0x1c = 0.0f).
# - lite_ystub (0x1f853dc -> 0x2749490): adds baked offset [x20, #0x1c] (0.0f outside OBS 30|4..5).
# - mtx_fix (0x1f71dc0 -> 0x27494a0): conjugates rotated local matrix by Sy = diag(1, k, 1) when 0.5 < k < 0.99.
_fitw_cave = (0x1e2d1002, 0x1e220802, 0x6e0c0440, _b(0x2749480 + 12, 0x9131ac))
_ystub_cave = (0x1e260863, 0xbd401e86, 0x1e262863, _b(0x2749490 + 12, 0x1f853e0))
_mtx_cave = (
    0xbd414a60, 0xbd414e61, 0x1e201822, 0x1e2c1003, 0x1e232040, 0x5400024d, 0x528e1489,
    0x72a7efa9, 0x1e270123, 0x1e232040, 0x540001aa, 0xbd400503, 0x1e220863, 0xbd000503,
    0xbd402503, 0x1e220863, 0xbd002503, 0xbd401103, 0x1e221863, 0xbd001103, 0xbd401903,
    0x1e221863, 0xbd001903, 0xb9410668, _b(0x27494a0 + 96, 0x1f71dc4),
)

VARIANT_CUTS = {
    '43': {
        _main: [
            (0x09131a8, '00040c6e', _hx((_b(0x9131a8, 0x2749480),)), '4:3 fitw root scaleobj sy = 0.75 * s'),
            (0x2749480, '00' * 16, _hx(_fitw_cave), '4:3 fitw cave'),
            (0x1f853dc, '6308261e', _hx((_b(0x1f853dc, 0x2749490),)), '4:3 ScreenLayout bake additive y stub'),
            (0x2749490, '00' * 16, _hx(_ystub_cave), '4:3 lite_ystub cave reading [so+0x1c]'),
            (0x1f71dc0, '680641b9', _hx((_b(0x1f71dc0, 0x27494a0),)), '4:3 rotated local matrix Sy conjugation'),
            (0x27494a0, '00' * 100, _hx(_mtx_cave), '4:3 mtx_fix cave'),
        ],
    },
}

BINDING = [
    {'what': 'Pokopia camera aspect hooks in main v2.0.1', 'now': 'build',
     'goal': 'game', 'purpose': 'rendering',
     'checked': 'main 76a489f3bd3642fa5e18bd83d32c98ba (Fold 7 observation, 2026-11-11)',
     'why': 'camera layout/offsets are specific to this exact game build',
     'blocked': 'future game builds require exact offset and original-word validation'},
    {'what': "Pokopia native 4:3 UI and camera variant (VARIANT_CUTS['43'] and OBS 30|3..5 in main v2.0.1)",
     'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'checked': 'main 76a489f3bd3642fa5e18bd83d32c98ba (kg175 disassembly & rewriter validation)',
     'why': 'hook offsets (0x9131a8, 0x1f853dc, 0x1f71dc0, 0x1f72270, 0x1f84fac/b4) and ScreenLayout pane offsets belong to this exact build',
     'blocked': 'one build on hand; future updates require offset and original-word validation'},
]