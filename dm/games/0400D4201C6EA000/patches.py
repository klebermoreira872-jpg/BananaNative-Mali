# Mario Tennis Fever, Switch 2 (0400D4201C6EA000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies those of a
# module's NSO build ID ("Registered patches" there). The game's code is one NRO, nro0, which main decodes at run time; the pack's rewrite of it is keyed by the NRO's build ID.

# 1.1.1 nro0: full game speed at low frame rates (Full game speed at low frame rates, game.tsv fps_decouple skip; dm/host/android/mtf_speed.c). Two observation gates on the frame
# function's GOT loads of its draw flag (nro0+0x17999bc): at the frame's start, before the flag's first read (the host decides whether the frame is skipped), and before the submit's
# read (it writes 0 there for a skipped frame: no submit, no present, the game's own interval min(n, 5) holds the next shown frame). Both words are position independent
_MTF_SKIP = 39   # OBS_MTF_SKIP in dm/host/dm.h; the parameter (bits 8 up) is which gate

# 1.1.1 nro0: the scenes' size below what the graphics scales give (Game settings > Resolution, Phone 540p; dm/host/android/mtf_size.c). One observation gate where the size function's
# paths join, after the graphics scale is applied (x20 the scene's size record, w9 its width). The callback does nothing unless the launcher passed a graphics size (DM_GRAPHICS_SIZE)
# smaller than the game's pick. The original word is position independent and checked by the rewriter
_MTF_SIZE = 34   # OBS_MTF_SIZE in dm/host/dm.h
# 1.1.1 nro0: the gameplay camera and the 2D layer follow the picture's shape (Game settings > Aspect ratio; dm/host/android/mtf_wide.c, GPL-3.0-or-later). Eight observation gates,
# the kind in the parameter's bits 5 up (0 camera 0's aspect store at a layout apply; 1 a projection builder's fovy just loaded, register in bits 0-4; 2 a layout's projection before
# its copy into the draw info; 3 nn::ui2d draw setup and 4 text setup, before their bl to the draw info's projection getter nro0+0x66718). The callback does nothing unless
# DM_VK_PICTURE_ASPECT is a shape other than 16:9. Every original word is position independent and checked by the rewriter (a bl site moves to the instruction before it)
_MTF_WIDE = 38   # OBS_MTF_WIDE in dm/host/dm.h
# 1.1.1 nro0: no glyph lost on frames the game does not draw (the half-rate mode fps_half_draw sets for a 30 fps cap; #302; dm/host/android/mtf_glyph.c). One observation gate on the
# glyph upload callback's store that marks the dirty-rect ring consumed (nro0+0x11ded2c, str w8,[x26,#4]): with the frame's draw flag at 0 the callback writes the read index into w8,
# so the rects stay pending for the next drawn frame. The original word is position independent and checked by the rewriter
_MTF_GLYPH = 40   # OBS_MTF_GLYPH in dm/host/dm.h
OBS = {
  '250a510a934129cb38e930c9a29082b6': [
    # HELD OUT of 0.3.40 (the skip costs the game's sound; README.md): the two _MTF_SKIP rows (0x11f8624, 0x11f932c) are in commit bd4f23f58
    (0x11ded2c, _MTF_GLYPH, 'b9000748', "glyph upload callback nro0+0x11deac0: the store marking the dirty-rect ring consumed (str w8,[x26,#4]); x26 the ring's write/read indices, w8 the write index"),
    (0x125eb98, _MTF_SIZE, 'b9410a6a', "scene size after the graphics scale (ldr w10,[x19,#0x108], where the scale paths join); x20 the size record (u16 width +0x1c, height +0x1e), w9 its width"),
    (0x11a2fc8, _MTF_WIDE | 0 << 13, 'bd004280', "display layout setter: camera 0's aspect store (str s0,[x20,#0x40]); x19 the layout (view count +0x24), x20 the camera array, s0 set before the store"),
    (0x932378, _MTF_WIDE | 1 << 13 | 1 << 8, '1e230821', "camera updater, table path: fmul s1,s1,s3 (s1 the fovy ldp s5,s1,[x19,#0x48] loaded at +0x931ef0); x19 the camera, s1 Vert+ in the register"),
    (0x93252c, _MTF_WIDE | 1 << 13 | 0 << 8, '1e2c1001', "camera updater, culling frustum: fmov s1,#0.5 after ldr s0,[x19,#0x4c] (fovy); s0 Vert+ in the register"),
    (0x932700, _MTF_WIDE | 1 << 13 | 0 << 8, '1e2c1001', "camera updater, second frustum (+0x2f8): fmov s1,#0.5 after ldr s0,[x19,#0x4c]; s0 Vert+ in the register"),
    (0x9334ac, _MTF_WIDE | 1 << 13 | 0 << 8, '1e2c1001', "camera refresh nro0+0x933358: fmov s1,#0.5 after ldr s0,[x19,#0x4c]; s0 Vert+ in the register"),
    (0x11d661c, _MTF_WIDE | 2 << 13, '3d800bf7', "layout draw info setup: str q23,[sp,#0x20] before bl nro0+0x665fc (the projection copy); x1 the stack matrix (x row first) scaled, x0 the draw info"),
    (0x75a98, _MTF_WIDE | 3 << 13, 'bd00df20', "nn::ui2d draw constant-buffer setup, before its bl to the projection getter; x0 the draw info, pane matrix x23, size x22 (a full-canvas pane reads a stand-in)"),
    (0x8a2ec, _MTF_WIDE | 4 << 13, 'a90d22c8', "nn::ui2d text setup, before its bl to the same getter; x0 the draw info, pane x21 (a full-canvas pane reads a stand-in)"),
  ],
}
BINDING = [
    {'what': "glyph uploads: the font cache's dirty-rect ring consumed only on drawn frames, so no upload is lost with a command buffer that is never submitted under the 30 fps cap (fps_half_draw)", 'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'why': "the upload callback, its ring and the draw flag are the game's own code and data at fixed addresses of this build; the host sees only the submits the game makes",
     'blocked': 'one build on hand; the callback could be found by function fingerprint (the +0x1c088 ring base, the blr with w1 = 0x33 and the ldr/str of the ring indices before its epilogue)'},
    {'what': 'frame skip: the draw flag of frames behind real time written 0, so the game steps at full speed below 60 fps (Full game speed at low frame rates)', 'now': 'build', 'goal': 'game', 'purpose': 'frame rate',
     'why': "the flag, the job table and the frame function are the game's own, at fixed addresses of this build; the engine counts frames and has no rate or step count the host could write",
     'blocked': "one build on hand; the frame function could be found by fingerprint (cmp w8,#5 and csel ..., lt before the bl to the helper that calls nvnWindowGet/SetPresentInterval, and the flag's ldrb; cbz before it)"},
    {'what': 'scene size: the scenes drawn below the smallest size the graphics scales give (Game settings > Resolution, Phone 540p)', 'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'why': "the size function is the game's own code at a fixed address of this build; no Horizon query gives a smaller size",
     'blocked': 'one build on hand; the join could be found by function fingerprint (the 4/5 and 2/3 multiplies after GetCurrentGraphicsScale)'},
    {'what': 'camera aspect and 2D layer: the gameplay camera and the layouts follow the picture shape (Game settings > Aspect ratio)', 'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'why': "the display layout setter, the camera's projection builders and the layout setup are the game's own code at fixed addresses of this build; the two nn::ui2d sites are SDK code a fingerprint finds (the same as Mario Kart World 1.8.0's)",
     'blocked': 'one build on hand; the setter could be found by function fingerprint (two ucvtf, ucvtf, fdiv, str s0 blocks from the layout\'s +0x2c and +0x34 into the camera array at +0x40 and +0x370)'},
]
