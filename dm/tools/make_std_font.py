#!/usr/bin/env python3
# Build the stand-in for the standard shared font (dm/third_party/fonts/NotoSans-Regular-subset.ttf, served as standard.ttf): Noto Sans Regular subset to Latin, Greek,
# Cyrillic and punctuation, with the arrows and mathematical operators of Noto Sans Math and the geometric shapes, miscellaneous symbols and dingbats of Noto Sans Symbols 2
# added for the code points Noto Sans has no glyph for. All three are SIL OFL 1.1 fonts of the Noto Project with no Reserved Font Name (dm/third_party/fonts/README.md).
# Why: Noto Sans alone has one glyph (U+25CC) in U+25A0-25FF; Echoes of Wisdom's font code asks for U+25A1 (WHITE SQUARE), gets no glyph and reads through the NULL
# (docs/reference/services.md, "A game crashes on a glyph the standard shared font lacks").
# Usage: make_std_font.py out.ttf NotoSans-Regular.ttf NotoSansMath-Regular.ttf NotoSansSymbols2-Regular.ttf (each from its release's hinted/ttf folder); needs fontTools 4.68.0
import sys
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.merge import Merger

def rng(*spans): return {c for a, b in spans for c in range(a, b + 1)}

# Noto Sans: the subset as it has been since NotoSans-v2.015 (the same pyftsubset options; it reproduces the earlier file byte for byte)
BASE = rng((0x20, 0x7E), (0xA0, 0x24F), (0x250, 0x2AF), (0x2B0, 0x2FF), (0x300, 0x36F), (0x370, 0x3FF), (0x400, 0x52F), (0x1E00, 0x1EFF), (0x1F00, 0x1FFF),
           (0x2000, 0x206F), (0x20A0, 0x20CF), (0x2100, 0x214F), (0x2150, 0x218F), (0x2190, 0x21FF), (0x2200, 0x22FF), (0x25A0, 0x25FF), (0x2600, 0x26FF),
           (0x2700, 0x27BF), (0xFFFD, 0xFFFD))
MATH = rng((0x2190, 0x21FF), (0x2200, 0x22FF))                       # arrows, mathematical operators
SYM2 = rng((0x2190, 0x21FF), (0x25A0, 0x25FF), (0x2600, 0x26FF), (0x2700, 0x27BF))   # what Math lacks of the arrows; geometric shapes, misc symbols, dingbats

def sub(path, cps, out, base):
    o = subset.Options()
    o.glyph_names = True; o.notdef_outline = True; o.name_IDs = ['*']
    if base: o.layout_features = ['kern', 'liga', 'ccmp', 'locl', 'mark', 'mkmk']; o.hinting = True
    else: o.layout_features = []; o.hinting = False; o.drop_tables += ['MATH', 'vhea', 'vmtx', 'gasp']   # symbols: no shaping, no hints (the merged font keeps Noto Sans's)
    f = subset.load_font(path, o)
    have = set(f.getBestCmap())
    s = subset.Subsetter(o); s.populate(unicodes=sorted(cps & have)); s.subset(f)
    subset.save_font(f, out, o)
    return set(TTFont(out).getBestCmap())

def main():
    if len(sys.argv) != 5: sys.exit(__doc__ or 'usage: make_std_font.py out.ttf NotoSans-Regular.ttf NotoSansMath-Regular.ttf NotoSansSymbols2-Regular.ttf')
    out, sans, math_, sym2 = sys.argv[1:]
    for p in (sans, math_, sym2):
        if TTFont(p)['head'].unitsPerEm != 1000: sys.exit(f'{p}: units per em is not 1000')
    tmp = [out + '.base.ttf', out + '.math.ttf', out + '.sym2.ttf']
    got = sub(sans, BASE, tmp[0], True)
    got |= sub(math_, MATH - got, tmp[1], False)
    got |= sub(sym2, SYM2 - got, tmp[2], False)
    f = Merger().merge(tmp)
    base = TTFont(tmp[0])
    src = base['head']   # (the merger stamps head.created / modified with the time: Noto Sans's own instead, so the same sources give the same bytes)
    f['head'].created, f['head'].modified = src.created, src.modified; f.recalcTimestamp = False
    # The line metrics stay Noto Sans's: the merger takes the extremes of the three, and Noto Sans Math's win ascent / descent (3105 / 2550, for its tall operators) made the
    # line 3.7 times as high, so the SDK's font engine, which fits glyphs to these metrics, drew all text squashed (Mario Kart 8 Deluxe's quit dialog). The added symbols are
    # drawn within Noto Sans's line like its own glyphs
    for k in ('ascent', 'descent', 'lineGap', 'advanceWidthMax'): setattr(f['hhea'], k, getattr(base['hhea'], k))
    for k in ('sTypoAscender', 'sTypoDescender', 'sTypoLineGap', 'usWinAscent', 'usWinDescent', 'sxHeight', 'sCapHeight', 'xAvgCharWidth'): setattr(f['OS/2'], k, getattr(base['OS/2'], k))
    f.save(out)
    import os
    for t in tmp: os.remove(t)
    cm = set(TTFont(out).getBestCmap())
    missing = sorted(BASE - cm)
    print(f'{out}: {len(cm)} code points, {os.path.getsize(out)} bytes; asked for and not in any of the three: {len(missing)}'
          + (f' (U+{missing[0]:04X}..U+{missing[-1]:04X})' if missing else ''))
    if 0x25A1 not in cm: sys.exit('U+25A1 (WHITE SQUARE) is missing')

if __name__ == '__main__': main()
