# fonts: stand-in shared fonts (open licence only)

`NotoSans-Regular-subset.ttf` is the stand-in the host serves for the shared-font types on Android (`dm/host/hle_sdk16.c`, `$DM_FONT_DIR/standard.ttf`), so that text no longer depends on the phone's `/system/fonts`. The launcher copies it into the app's files folder and sets `DM_FONT_DIR` to it (`android/app/build.gradle` `nxFontAssets`, `GameFonts.java`).

Nintendo's fonts are never included, downloaded or imitated here.

| | |
|---|---|
| Font | Noto Sans Regular, static hinted TrueType (glyf outlines, no `fvar`), with the symbols Noto Sans has no glyph for merged in unhinted from Noto Sans Math and Noto Sans Symbols 2 (all three 1000 units per em) |
| Versions | NotoSans-v2.015 (notofonts/latin-greek-cyrillic release, 2024-11-20); NotoSansMath-v3.000 (notofonts/math, 2024-06-05); NotoSansSymbols2-v2.008 (notofonts/symbols, 2023-10-13). 2952 glyphs, 2715 code points |
| Sources | https://github.com/notofonts/latin-greek-cyrillic/releases/download/NotoSans-v2.015/NotoSans-v2.015.zip (zip sha256 `0c34df072a3fa7efbb7cbf34950e1f971a4447cffe365d3a359e2d4089b958f5`), file `NotoSans/hinted/ttf/NotoSans-Regular.ttf` (621,572 bytes)<br>https://github.com/notofonts/math/releases/download/NotoSansMath-v3.000/NotoSansMath-v3.000.zip (zip sha256 `ac351837b41f8a897f020b97fb0f075ad574c1e9669fb5839ada1f92fd748356`), file `NotoSansMath/hinted/ttf/NotoSansMath-Regular.ttf` (990,564 bytes)<br>https://github.com/notofonts/symbols/releases/download/NotoSansSymbols2-v2.008/NotoSansSymbols2-v2.008.zip (zip sha256 `346c930bbe8eb946701a05c54e9c11a2094dee1d93c387bf1771c0a3e335688f`), file `NotoSansSymbols2/hinted/ttf/NotoSansSymbols2-Regular.ttf` (671,568 bytes) |
| This file | `NotoSans-Regular-subset.ttf`, 445,808 bytes, sha256 `11fc34402f4ac7c69bf0e1f5b8b43e9a109ee3fc604a60fe5b96beedc1dd6604` |
| Licence | SIL Open Font License 1.1, `OFL.txt`: the three releases ship the same licence text, each with its own copyright line, and all three lines are in the file. No copyright line names a Reserved Font Name, so the merged font keeps Noto Sans's name |

Coverage: Basic Latin, Latin-1, Latin Extended A/B, IPA, spacing modifiers, combining marks, Greek, Cyrillic (with supplement), Latin Extended Additional, Greek Extended, general punctuation, currency, letterlike, number forms and U+FFFD from Noto Sans; arrows (U+2190-21FF) and mathematical operators (U+2200-22FF) from Noto Sans Math; geometric shapes (U+25A0-25FF, all 96), and those of the miscellaneous symbols (U+2600-26FF) and dingbats (U+2700-27BF) it has, from Noto Sans Symbols 2. No CJK, no Hangul, no private-use icons. Noto Sans itself has one geometric shape (U+25CC) and no arrows, operators, symbols or dingbats: the subset before the merge left them out without saying so, and Echoes of Wisdom's font code, asking for U+25A1, read through the missing glyph ([A game crashes on a glyph the standard shared font lacks](../../../docs/reference/services.md#a-game-crashes-on-a-glyph-the-standard-shared-font-lacks)).

Reproduce (fonttools 4.68.0, in a venv outside the repository; the same sources give the same bytes):

```
python3 dm/tools/make_std_font.py NotoSans-Regular-subset.ttf \
  NotoSans/hinted/ttf/NotoSans-Regular.ttf NotoSansMath/hinted/ttf/NotoSansMath-Regular.ttf NotoSansSymbols2/hinted/ttf/NotoSansSymbols2-Regular.ttf
```

The script's Noto Sans part is the earlier `pyftsubset` command (the same code points and options), which alone reproduces the previous file (sha256 `5d9684f4...`); its glyphs, metrics and hinting are unchanged in the merged font. The line metrics (`hhea` ascent, descent and line gap; `OS/2` typo and win ascent and descent) stay Noto Sans's too: the merger takes the extremes of the three fonts, and Noto Sans Math's win ascent and descent (3105 / 2550) made the SDK's font engine draw all text squashed (Mario Kart 8 Deluxe's quit dialog, the first build of this font).
