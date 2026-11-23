"""Fire Emblem Fortune's Weave v131072 (main db93b0125f4850601d61c3edde012f8e).

VARIANT_CUTS['43']: a native 4:3 mod (game.tsv `variant 43`, the launcher's Game settings › Aspect ratio). The game keeps its 16:9
window and scene sizes; its cameras take a 4:3 aspect and its UI is laid out for 4:3 inside the 16:9 frame, which the present then
shows at 4:3 (DM_VK_PICTURE_ASPECT=4:3: it fills a 4:3 screen and gets side bars on a 16:9 one). The words started as a .pchtxt
for Eden-family emulators (camera aspect, ui2d pane rules) and were extended here; each group below says what it fixes. The
original bytes are kept so the rewriter refuses another executable."""

# Minimap rotation: v11 pinned N_RotCenter's Z rotation (+0x44) at 180 degrees, taking the game's turning of the map with the camera for a
# fault. The game places the quest pins (N_Quest, outside N_RotCenter) with its own angle, so they slid across the pinned map while walking and
# turning, and the map was the wrong way round for the camera. N_RotCenter now only skips the pane rules (0x58f570) and keeps its rotation;
# the scissor fix below keeps the turning map inside its frame. Checked in Dagsion against 16:9 through a walk and a camera turn.
# Camera aspect and ui2d pane rules (v11). The ui2d rules: a pane at |y| >= 120 under a parent at global (0,0) moves 180 units toward
# the nearer top or bottom edge (the "edge rule"), a centred full-screen pane (>= 1896 x 960) gets its y scaled by 4/3 (the
# "overlay rule"), sliding 30x40 containers count as anchored; a few names are exempt (L_UnitIn*, L_Cursor*, L_Popup_*).
_V11 = [
    (0x00b51e38, '2118221e', '01102d1e', 'v11 camera and UI'),
    (0x0055b424, '00000000', '4c1440b9', 'v11 camera and UI'),
    (0x0055b428, '00000000', 'cd3a9752', 'v11 camera and UI'),
    (0x0055b42c, '00000000', '4d5ea772', 'v11 camera and UI'),
    (0x0055b430, '00000000', '9f010d6b', 'v11 camera and UI'),
    (0x0055b434, '00000000', 'c1250054', 'v11 camera and UI'),
    (0x0055b438, '00000000', '4c0040b9', 'v11 camera and UI'),
    (0x0055b43c, '00000000', '72100014', 'v11 camera and UI'),
    (0x0055f604, '00000000', '2d119152', 'v11 camera and UI'),
    (0x0055f608, '00000000', '0d51a772', 'v11 camera and UI'),
    (0x0055f60c, '00000000', '9f010d6b', 'v11 camera and UI'),
    (0x0055f610, '00000000', 'e116fe54', 'v11 camera and UI'),
    (0x0055f614, '00000000', '5a04c03d', 'v11 camera and UI'),
    (0x0055f618, '00000000', '1b102d1e', 'v11 camera and UI'),
    (0x0055f61c, '00000000', 'dbf8ff17', 'v11 camera and UI'),
    (0x0055d988, '00000000', '5a939b4f', 'v11 camera and UI'),
    (0x0055d98c, '00000000', '5a04803d', 'v11 camera and UI'),
    (0x0055d990, '00000000', '089840b9', 'v11 camera and UI'),
    (0x0055d994, '00000000', '40fcff17', 'v11 camera and UI'),
    (0x0055b8ec, '00000000', '089840b9', 'v11 camera and UI'),
    (0x0055b8f0, '00000000', '69040014', 'v11 camera and UI'),
    (0x0055ca90, '089840b9', '65faff17', 'v11 camera and UI'),
    (0x0058e724, '00000000', '0b5840f9', 'v11 camera and UI'),
    (0x0058e728, '00000000', 'cae98bd2', 'v11 camera and UI'),
    (0x0058e72c, '00000000', '4aeaadf2', 'v11 camera and UI'),
    (0x0058e730, '00000000', '8a6ec8f2', 'v11 camera and UI'),
    (0x0058e734, '00000000', 'aaccedf2', 'v11 camera and UI'),
    (0x0058e738, '00000000', '8c030014', 'v11 camera and UI'),
    (0x0058f568, '00000000', '7f010aeb', 'v11 camera and UI'),
    (0x0058f56c, '00000000', 'c1ae0954', 'v32: b.ne 0x5a2b44 (the part subtree check first; v11 had b.ne 0x586344)'),
    (0x0058f570, '00000000', 'c1fbff17', 'minimap: b 0x58e474 (N_RotCenter keeps the game rotation; v11 wrote 180 to +0x44)'),
    (0x00586344, '00000000', '890904b4', 'v11 camera and UI'),
    (0x00586348, '00000000', '101d40bd', 'v11 camera and UI'),
    (0x0058634c, '00000000', '110d40bd', 'v11 camera and UI'),
    (0x00586350, '00000000', '0822201e', 'v11 camera and UI'),
    (0x00586354, '00000000', '81031d54', 'v15: b.ne 0x5c03c4 (parent off y=0: N_Player_Bg*/N_Target_Bg* check; v11 had b.ne 0x58e474)'),
    (0x0058faa4, '00000000', '2822201e', 'v11 camera and UI'),
    (0x0058faa8, '00000000', '614eff54', 'v11 camera and UI'),
    (0x0058faac, '00000000', 'a6520014', 'v12: b 0x5a4544 (A_Contents check; v11 had mov x10, #0x5f4c)'),
    (0x0058fab0, '00000000', '6aa8aef2', 'v11 camera and UI'),
    (0x0058fab4, '00000000', '4a6ecef2', 'v11 camera and UI'),
    (0x0058fab8, '00000000', 'ea4deef2', 'v11 camera and UI'),
    (0x0058fabc, '00000000', '2a000014', 'v11 camera and UI'),
    (0x0058fb64, '00000000', '7f010aeb', 'v11 camera and UI'),
    (0x0058fb68, '00000000', '6048ff54', 'v11 camera and UI'),
    (0x0058fb6c, '00000000', 'aacaadf2', 'v11 camera and UI'),
    (0x0058fb70, '00000000', '2a8dcef2', 'v11 camera and UI'),
    (0x0058fb74, '00000000', '2ac9edf2', 'v11 camera and UI'),
    (0x0058fb78, '00000000', '73f3ff17', 'v11 camera and UI'),
    (0x0058c944, '00000000', '7f010aeb', 'v11 camera and UI'),
    (0x0058c948, '00000000', '00580154', 'v36: b.eq 0x58f448 (L_UnitIn*: the layout y test first; v11 had b.eq 0x58e474)'),
    (0x0058c94c, '00000000', '0aeaadf2', 'v11 camera and UI'),
    (0x0058c950, '00000000', '0aaecef2', 'v11 camera and UI'),
    (0x0058c954, '00000000', '0aeeebf2', 'v11 camera and UI'),
    (0x0058c958, '00000000', 'b31a0014', 'v11 camera and UI'),
    (0x00593424, '00000000', '7f010aeb', 'v11 camera and UI'),
    (0x00593428, '00000000', '6082fd54', 'v11 camera and UI'),
    (0x0059342c, '00000000', '2d698cd2', 'v11 camera and UI'),
    (0x00593430, '00000000', 'edcdadf2', 'v11 camera and UI'),
    (0x00593434, '00000000', 'cde8cdf2', 'v11 camera and UI'),
    (0x00593438, '00000000', '4d6eecf2', 'v11 camera and UI'),
    (0x0059343c, '00000000', '0a590014', 'v14: b 0x5a9864 (Player_/Target_Fade check; v11 had b 0x58f004)'),
    (0x0058f004, '00000000', '102a221e', 'v11 camera and UI'),
    (0x0058f008, '00000000', '7f010deb', 'v11 camera and UI'),
    (0x0058f00c, '00000000', 'c0adff54', 'v11 camera and UI'),
    (0x0058f010, '00000000', '0a5ea852', 'v11 camera and UI'),
    (0x0058f014, '00000000', '5201271e', 'v11 camera and UI'),
    (0x0058f018, '00000000', '11c2201e', 'v11 camera and UI'),
    (0x0058f01c, '00000000', '6dfdff17', 'v11 camera and UI'),
    (0x0058e5c4, '00000000', '8a66a852', 'v11 camera and UI'),
    (0x0058e5c8, '00000000', '5101271e', 'v11 camera and UI'),
    (0x0058e5cc, '00000000', 'a6ffff17', 'v11 camera and UI'),
    (0x0058e5d0, '00000000', '2022321e', 'v11 camera and UI'),
    (0x0058e5d4, '00000000', '0bf5ff54', 'v11 camera and UI'),
    (0x0058e5d8, '00000000', 'fbffff17', 'v11 camera and UI'),
    (0x0058e464, '00000000', '88640114', 'v28: b 0x5e7684 (the QuestTalk Wdw check before the edge move; v11 had fneg s19, s17)'),
    (0x0058e468, '00000000', '0822201e', 'v11 camera and UI'),
    (0x0058e46c, '00000000', '31ce331e', 'v11 camera and UI'),
    (0x0058e470, '00000000', '4228311e', 'v11 camera and UI'),
    (0x0058e474, '00000000', '0318472d', 'v11 camera and UI'),
    (0x0058e478, '00000000', '80010014', 'v11 camera and UI'),
    (0x0058ea74, '0318472d', '2cffff17', 'v11 camera and UI'),
    (0x005749c4, '00000000', '091040b9', 'v11 camera and UI'),
    (0x005749c8, '00000000', '2a119152', 'v11 camera and UI'),
    (0x005749cc, '00000000', '0a51a772', 'v11 camera and UI'),
    (0x005749d0, '00000000', '3f010a6b', 'v11 camera and UI'),
    (0x005749d4, '00000000', '81340354', 'v11 camera and UI'),
    (0x005749d8, '00000000', 'd3ffff17', 'v11 camera and UI'),
    (0x00574924, '00000000', '092440b9', 'v11 camera and UI'),
    (0x00574928, '00000000', 'ca3a9752', 'v11 camera and UI'),
    (0x0057492c, '00000000', '4a5ea772', 'v11 camera and UI'),
    (0x00574930, '00000000', '3f010a6b', 'v11 camera and UI'),
    (0x00574934, '00000000', '81390354', 'v11 camera and UI'),
    (0x00574938, '00000000', '0bffff17', 'v11 camera and UI'),
    (0x00574564, '00000000', '0008c03d', 'v11 camera and UI'),
    (0x00574568, '00000000', '01102d1e', 'v11 camera and UI'),
    (0x0057456c, '00000000', '0090814f', 'v11 camera and UI'),
    (0x00574570, '00000000', '0008803d', 'v11 camera and UI'),
    (0x00574574, '00000000', 'bc1a0014', 'v11 camera and UI'),
    (0x0057b064, '00000000', '008440ad', 'v11 camera and UI'),
    (0x0057b068, '00000000', 'afeeff17', 'v11 camera and UI'),
    (0x00576b20, '008440ad', 'a9f7ff17', 'v11 camera and UI'),
    (0x00586358, '00000000', '8ba9ff17', 'v11 camera and UI'),
    (0x00570984, '00000000', '2822201e', 'v11 camera and UI'),
    (0x0057098c, '00000000', '122840fd', 'v11 camera and UI'),
    (0x00570990, '00000000', 'aa9da852', 'v11 camera and UI'),
    (0x00570994, '00000000', '5301271e', 'v11 camera and UI'),
    (0x00570998, '00000000', '8b340014', 'v11 camera and UI'),
    (0x0057dbc4, '00000000', '4022331e', 'v11 camera and UI'),
    (0x0057dbcc, '00000000', '52060c5e', 'v11 camera and UI'),
    (0x0057dbd0, '00000000', '0a8ea852', 'v11 camera and UI'),
    (0x0057dbd4, '00000000', '5301271e', 'v11 camera and UI'),
    (0x0057dbd8, '00000000', '4022331e', 'v11 camera and UI'),
    (0x0057dbdc, '00000000', '1a050014', 'v11 camera and UI'),
    (0x0057f048, '00000000', '37330114', 'v18: b 0x5cbd24 (UnitPub check, then the v12 L_List check at 0x5a18a4)'),
    (0x0057f04c, '00000000', '4af5a772', 'v11 camera and UI'),
    (0x0057f050, '00000000', '5301271e', 'v11 camera and UI'),
    (0x0057f054, '00000000', '2108331e', 'v11 camera and UI'),
    (0x0056ce04, '00000000', '2c2940f9', 'v11 camera and UI'),
    (0x0056ce08, '00000000', '0a3ea8d2', 'v11 camera and UI'),
    (0x0056ce0c, '00000000', '0a44e8f2', 'v11 camera and UI'),
    (0x0056ce10, '00000000', '9f010aeb', 'v11 camera and UI'),
    (0x0056ce14, '00000000', '81951d54', 'v13: b.ne 0x5a80c4 (empty sliding parent check)'),
    (0x0056ce18, '00000000', 'dd0e0014', 'v11 camera and UI'),
    (0x00570988, '00000000', 'e123fe54', 'v11 camera and UI'),
    (0x0057dbc8, '00000000', 'eb051554', 'v12: b.lt 0x5a7c84 (tall-pane overlay check; v11 had b.lt 0x58faac)'),
    (0x0057f044, '00000000', '0bd12554', 'v18: b.lt 0x5caa64 (under 960 tall: the Fade check; v11 had b.lt 0x58faac)'),
    (0x0057f058, '00000000', '95420014', 'v11 camera and UI'),
]

# v12 UI fixes, with the v11 entry words at 0x57f048 and 0x58faac above redirected:

# - L_List: v10's full-screen overlay rule (centred pane >= 1896x960 gets y scale x4/3) caught the Base Menu's 2694x1120 list container;
#   the game places the menu cursor at (target global - parent global) without the parent's scale, so the cursor drifted further below
#   the selected entry with every step down. Panes whose name starts with L_Li are now left unscaled (caves 0x5a18a4, 0x5a3c84).
# - A_Contents: v4's HUD rule (|y| >= 120 under a parent at (0,0) moves 180 units toward the edge) moved dialog text (T_Text at y 180 in
#   A_Contents) out of its window ("You cannot fast-travel at this time." above the box). Children of A_Contents are now left in place
#   (caves 0x5a4544, 0x5a6864). Both found by reading the live pane trees in a PC emulator and verified there.

_UI_V12 = [

    (0x005a18a4, '00000000', '0ab040b9', 'v12: ldr w10, [x0, #0xb0]'),

    (0x005a18a8, '00000000', '5201271e', 'v12: fmov s18, w10'),

    (0x005a18ac, '00000000', '8ae98b52', 'v12: mov w10, #0x5f4c'),

    (0x005a18b0, '00000000', '8a29ad72', 'v12: movk w10, #0x694c, lsl #16'),

    (0x005a18b4, '00000000', '5301271e', 'v12: fmov s19, w10'),

    (0x005a18b8, '00000000', '4022331e', 'v12: fcmp s18, s19'),

    (0x005a18bc, '00000000', 'f2080014', 'v12: b #0x5a3c84'),

    (0x005a3c84, '00000000', '40f1f554', 'v12: b.eq #0x58faac'),

    (0x005a3c88, '00000000', '6a559552', 'v12: mov w10, #0xaaab'),

    (0x005a3c8c, '00000000', '7eac0114', 'v32: b 0x60ee84 (the Parts pane check before the stretch; v12 had b #0x57f04c)'),

    (0x005a4544, '00000000', '2c5940f9', 'v12: ldr x12, [x9, #0xb0]'),

    (0x005a4548, '00000000', '2ae88bd2', 'v12: mov x10, #0x5f41'),

    (0x005a454c, '00000000', '6ae8adf2', 'v12: movk x10, #0x6f43, lsl #16'),

    (0x005a4550, '00000000', 'ca8dcef2', 'v12: movk x10, #0x746e, lsl #32'),

    (0x005a4554, '00000000', 'aaccedf2', 'v12: movk x10, #0x6e65, lsl #48'),

    (0x005a4558, '00000000', '9f010aeb', 'v12: cmp x12, x10'),

    (0x005a455c, '00000000', 'da7c0014', 'v16: b 0x5c38c4 (A_Contents / N_Status parent check; v12 had b 0x5a6864)'),

    (0x005a6864, '00000000', '80e0f354', 'v12: b.eq #0x58e474'),

    (0x005a6868, '00000000', '8ae98bd2', 'v12: mov x10, #0x5f4c'),

    (0x005a686c, '00000000', '91a4ff17', 'v12: b #0x58fab0'),

    # Tall overlays: v10 scaled a centred pane only when it was at least 1896 wide AND 960 tall; the shop's Fade01 (958x1080, the left
    # half dimmer) failed the width test and stayed short. A pane at least 1080 tall now passes alone (cave 0x5a7c84)
    (0x005a7c84, '00000000', '53060c5e', 'v12: mov s19, v18.s[1]'),
    (0x005a7c88, '00000000', 'ea90a852', 'v12: mov w10, #0x44870000 (1080.0)'),
    (0x005a7c8c, '00000000', '5101271e', 'v12: fmov s17, w10'),
    (0x005a7c90, '00000000', '6022311e', 'v12: fcmp s19, s17'),
    (0x005a7c94, '00000000', 'caf9ea54', 'v12: b.ge 0x57dbcc'),
    (0x005a7c98, '00000000', '859fff17', 'v12: b 0x58faac'),
]


# The Armorer's Buy/Sell and message panes have empty parents that slide horizontally.
# Apply the same vertical anchor during their slide as when they reach x=0.
_UI_V13 = [
    (0x005a80c4, '00000000', '30460014', 'v15: b 0x5b9984 (sliding parent 0x0 or 422x4; v13 had cbnz x12, 0x58e474)'),
    (0x005a80c8, '00000000', '3122ff17', 'v13: b 0x57098c'),
]


# v14: combat HUD smoke. The combat screen's Player_Fade / Target_Fade (960x536 smoky bands at y -40 in N_*_Bg) sit
# under a parent at (0,0) but have |y| < 120, so v4's edge rule left them while the names, HP bars and stats above them moved 180 toward
# the bottom edge: the smoke floated above the text. Panes named Player_Fade / Target_Fade now always take the move (caves 0x5a9864,
# 0x5b0744, 0x5b0be4: compare the pane name's first 8 bytes, then 'ade'; join the IconForc* path at 0x58e5c4). Verified in a PC emulator.
_UI_V14 = [
    (0x005a9864, '00000000', '0a8a8dd2', 'v14: mov x10, #0x6c50'),
    (0x005a9868, '00000000', '2a2caff2', 'v14: movk x10, #0x7961, lsl #16'),
    (0x005a986c, '00000000', 'aa4ccef2', 'v14: movk x10, #0x7265, lsl #32'),
    (0x005a9870, '00000000', 'eacbe8f2', 'v14: movk x10, #0x465f, lsl #48'),
    (0x005a9874, '00000000', '7f010aeb', 'v14: cmp x11, x10'),
    (0x005a9878, '00000000', '609b0354', 'v14: b.eq #0x5b0be4'),
    (0x005a987c, '00000000', 'b21b0014', 'v14: b #0x5b0744'),
    (0x005b0744, '00000000', '8a2a8cd2', 'v14: mov x10, #0x6154'),
    (0x005b0748, '00000000', '4aeeacf2', 'v14: movk x10, #0x6772, lsl #16'),
    (0x005b074c, '00000000', 'aa8ccef2', 'v14: movk x10, #0x7465, lsl #32'),
    (0x005b0750, '00000000', 'eacbe8f2', 'v14: movk x10, #0x465f, lsl #48'),
    (0x005b0754, '00000000', '7f010aeb', 'v14: cmp x11, x10'),
    (0x005b0758, '00000000', '60240054', 'v14: b.eq #0x5b0be4'),
    (0x005b075c, '00000000', '2a7aff17', 'v14: b #0x58f004'),
    (0x005b0be4, '00000000', '0cb840b9', 'v14: ldr w12, [x0, #0xb8]'),
    (0x005b0be8, '00000000', '2a8c8c52', 'v14: mov w10, #0x6461'),
    (0x005b0bec, '00000000', 'aa0ca072', 'v14: movk w10, #0x65, lsl #16'),
    (0x005b0bf0, '00000000', '9f010a6b', 'v14: cmp w12, w10'),
    (0x005b0bf4, '00000000', '8120ef54', 'v14: b.ne #0x58f004'),
    (0x005b0bf8, '00000000', '102a221e', 'v14: fadd s16, s16, s2'),
    (0x005b0bfc, '00000000', '7276ff17', 'v14: b #0x58e5c4'),
]

# Scissor panes at 4:3 (with the v11 words): ui2d's scissor-pane draw (main+0x5975a0) turns the pane's global matrix into a pixel
# scissor without the v11 UI squeeze, so the Dagsion minimap's S_Scissor (256x256 at y 553) clipped 1626,0 256x115 instead of
# 29..221: the map spilled above its frame and its lower half was cut (also in PC emulators). On a screen-sized target (16:9, at least
# 720 high: handheld 1920x1080, docked 2048x1152, 1280x720; s5 x s4 is the target's size) the pane's y scale (s16) and y translation
# (s6) get the same 0.75 as the projection; other targets keep the game's scissor. Caves 0x59afa4 and 0x59c544 (7 words each, all used)
_SCISSOR43 = [
    (0x005975ec, '450c251e', '6e0e0014', 'scissor 4:3: b 0x59afa4'),
    (0x0059afa4, '00000000', '450c251e', 'scissor 4:3: fcsel s5, s2, s5, eq (moved)'),
    (0x0059afa8, '00000000', '8a00381e', 'scissor 4:3: fcvtzs w10, s4 (target height)'),
    (0x0059afac, '00000000', 'a900381e', 'scissor 4:3: fcvtzs w9, s5 (target width)'),
    (0x0059afb0, '00000000', '5f410b71', 'scissor 4:3: cmp w10, #720'),
    (0x0059afb4, '00000000', 'eb31fe54', 'scissor 4:3: b.lt 0x5975f0'),
    (0x0059afb8, '00000000', '4a6d1c53', 'scissor 4:3: lsl w10, w10, #4 (height x 16)'),
    (0x0059afbc, '00000000', '62050014', 'scissor 4:3: b 0x59c544'),
    (0x0059c544, '00000000', '290d090b', 'scissor 4:3: add w9, w9, w9, lsl #3 (width x 9)'),
    (0x0059c548, '00000000', '3f010a6b', 'scissor 4:3: cmp w9, w10 (16:9)'),
    (0x0059c54c, '00000000', '2185fd54', 'scissor 4:3: b.ne 0x5975f0'),
    (0x0059c550, '00000000', '15102d1e', 'scissor 4:3: fmov s21, #0.75'),
    (0x0059c554, '00000000', '100a351e', 'scissor 4:3: fmul s16, s16, s21'),
    (0x0059c558, '00000000', 'c608351e', 'scissor 4:3: fmul s6, s6, s21'),
    (0x0059c55c, '00000000', '25ecff17', 'scissor 4:3: b 0x5975f0'),
]

# v15:
# - EXP panel pop-in: Battle_Exp_In slides N_IO (422x4) from x -100 to 0; v11/v13 only treat 30x40 and 0x0 sliding parents as anchored,
#   so for the slide the name/EXP panel sat at its 16:9 height and jumped 180 down at x=0. 422x4 parents now count too (cave 0x5b9984).
# - Combat HUD flag and smoke: N_Player_Bg / N_Target_Bg (and *_Bg_Pos) animate between y 0 and -80. At -80 the edge rule skipped all
#   their children (it needs a parent at global y 0), so IconForcesSymbol_*, *_Bg00/01 and *_Fade stayed 180 above the moved names and
#   battle report (forecast, Blaze Arts, some combat phases). Under those parents the rule now runs as under (0,0); their own -80 is below
#   the 120 threshold, so nothing moves twice (caves 0x5c03c4, 0x5c2ce4, 0x5c3284). Found from the layouts in Layout/Battle.arc and the live pane trees.
_UI_V15 = [
    (0x005b9984, '00000000', '4c80dbb4', 'v15: cbz x12, 0x57098c (0x0 parent: anchor)'),
    (0x005b9988, '00000000', '6a7aa8d2', 'v15: x10 = 422x4 (Battle_Exp N_IO / N_Animal_IO)'),
    (0x005b998c, '00000000', '0a10e8f2', 'v15: movk x10, #0x4080, lsl #48'),
    (0x005b9990, '00000000', '9f010aeb', 'v15: cmp x12, x10'),
    (0x005b9994, '00000000', 'c07fdb54', 'v15: b.eq 0x57098c (422x4 parent: anchor)'),
    (0x005b9998, '00000000', 'b752ff17', 'v15: b 0x58e474 (other parents: leave)'),
    (0x005c03c4, '00000000', '2c5940f9', 'v15: ldr x12, [x9, #0xb0] (parent name)'),
    (0x005c03c8, '00000000', 'cae98bd2', 'v15: x10 = "N_Player"'),
    (0x005c03cc, '00000000', '0a8aadf2', 'v15: movk x10, #0x6c50, lsl #16'),
    (0x005c03d0, '00000000', '2a2ccff2', 'v15: movk x10, #0x7961, lsl #32'),
    (0x005c03d4, '00000000', 'aa4ceef2', 'v15: movk x10, #0x7265, lsl #48'),
    (0x005c03d8, '00000000', 'cde98bd2', 'v15: x13 = "N_Target"'),
    (0x005c03dc, '00000000', '420a0014', 'v15: b 0x5c2ce4'),
    (0x005c2ce4, '00000000', '8d2aacf2', 'v15: movk x13, #0x6154, lsl #16'),
    (0x005c2ce8, '00000000', '4deeccf2', 'v15: movk x13, #0x6772, lsl #32'),
    (0x005c2cec, '00000000', 'ad8ceef2', 'v15: movk x13, #0x7465, lsl #48'),
    (0x005c2cf0, '00000000', '9f010aeb', 'v15: cmp x12, x10'),
    (0x005c2cf4, '00000000', '84114dfa', 'v15: ccmp x12, x13, #4, ne (N_Player or N_Target)'),
    (0x005c2cf8, '00000000', '611b0854', 'v21: b.ne 0x5d3064 (other parents: the footer tolerance, then leave; v15 had b.ne 0x58e474)'),
    (0x005c2cfc, '00000000', '62010014', 'v15: b 0x5c3284'),
    (0x005c3284, '00000000', '2cb940b9', 'v15: ldr w12, [x9, #0xb8] (name bytes 8..11)'),
    (0x005c3288, '00000000', '8c5d0012', 'v15: and w12, w12, #0xffffff'),
    (0x005c328c, '00000000', 'ea4b8852', 'v15: w10 = "_Bg"'),
    (0x005c3290, '00000000', 'ea0ca072', 'v15: movk w10, #0x67, lsl #16'),
    (0x005c3294, '00000000', '9f010a6b', 'v15: cmp w12, w10'),
    (0x005c3298, '00000000', 'e18ee554', 'v15: b.ne 0x58e474'),
    (0x005c329c, '00000000', 'bab5fe17', 'v15: b 0x570984 (N_*_Bg / N_*_Bg_Pos: edge rule as under (0,0))'),
]

# v16: level-up window. Common_LvUpStatusWdw's T_UnitName (y 258 under N_Status at (0,0)) took v4's 180 move while its
# window Wdw_Status (y 90) and the stat rows (y <= 118) did not: the unit's name floated above the panel. Children of a parent named
# exactly N_Status are now left in place (caves 0x5c38c4, 0x5c6a24, entry 0x5a455c after the A_Contents check).
_UI_V16 = [
    (0x005c38c4, '00000000', '805de554', 'v16: b.eq 0x58e474 (A_Contents children: leave)'),
    (0x005c38c8, '00000000', 'cae98bd2', 'v16: x10 = "N_Status"'),
    (0x005c38cc, '00000000', '6a8aaef2', 'v16: movk x10, #0x7453, lsl #16'),
    (0x005c38d0, '00000000', '2a8ccef2', 'v16: movk x10, #0x7461, lsl #32'),
    (0x005c38d4, '00000000', 'aa6eeef2', 'v16: movk x10, #0x7375, lsl #48'),
    (0x005c38d8, '00000000', '9f010aeb', 'v16: cmp x12, x10'),
    (0x005c38dc, '00000000', '520c0014', 'v16: b 0x5c6a24'),
    (0x005c6a24, '00000000', '011f0054', 'v17: b.ne 0x5c6e04 (not N_Status: L_UnitIn* check; v16 had b.ne 0x5a6868)'),
    (0x005c6a28, '00000000', '2ce14239', 'v16: ldrb w12, [x9, #0xb8] (name byte 8)'),
    (0x005c6a2c, '00000000', '4cd2e334', 'v16: cbz w12, 0x58e474 (exactly N_Status: leave)'),
    (0x005c6a30, '00000000', '8e7fff17', 'v16: b 0x5a6868'),
]

# v17: unit detail screen (X on a unit). Battle_UnitInfoDetail's L_UnitInfo (3400x1625) takes v10's x4/3 y stretch; inside
# it the header L_UnitInfoDetail is exempt from v4's move by v11's L_UnitIn name rule, but its sibling N_Status (the stat windows, y 226)
# was stretched and moved, so the windows rode 240 up into the header. Children of a parent named L_UnitIn* are now left in place, as
# the pane itself is (cave 0x5c6e04 after the v16 N_Status check). The only other such parent at (0,0) (L_UnitInfo00) has children
# within +-120, so it is unchanged. Found from the live pane trees.
_UI_V17 = [
    (0x005c6e04, '00000000', '8ae98bd2', 'v17: x10 = "L_UnitIn"'),
    (0x005c6e08, '00000000', 'aacaadf2', 'v17: movk x10, #0x6e55, lsl #16'),
    (0x005c6e0c, '00000000', '2a8dcef2', 'v17: movk x10, #0x7469, lsl #32'),
    (0x005c6e10, '00000000', '2ac9edf2', 'v17: movk x10, #0x6e49, lsl #48'),
    (0x005c6e14, '00000000', '9f010aeb', 'v17: cmp x12, x10'),
    (0x005c6e18, '00000000', 'e0b2e354', 'v17: b.eq 0x58e474 (children of L_UnitIn*: leave)'),
    (0x005c6e1c, '00000000', 'd22d0014', 'v20: b 0x5d2564 (MenuItemList check; v17 had b 0x5a6868)'),
]

# v18: obelisks (Obelisk_Hero). The darkening Fade (1920x856 at y -112) is under the overlay rule's 960 and under the edge rule's 120, so it
# kept its 16:9 extent and the 4:3 screen's bottom 180 units stayed lit; a full-width pane named exactly Fade now takes the overlay's x4/3
# (cave 0x5caa64, from 0x57f044). The Flame Lord art UnitPub (1000x1110, taller than 1080) was caught by the overlay rule and drawn 4/3 too
# tall; a pane named exactly UnitPub is now left unscaled (cave 0x5cbd24, from 0x57f048).
# v19: the obelisk Fade is also moved 180 down (its 4/3 stretch about its own centre left the bottom lit), caves 0x5caa64, 0x5cd904.
_UI_V18 = [
    (0x005caa64, '00000000', 'ca288c52', 'v19: w10 = "Fade" (name bytes 0..3)'),
    (0x005caa68, '00000000', '8aacac72', 'v19: movk w10, #0x6564, lsl #16'),
    (0x005caa6c, '00000000', '7f010a6b', 'v19: cmp w11, w10'),
    (0x005caa70, '00000000', 'e181e254', 'v19: others: as before'),
    (0x005caa74, '00000000', '7f1d60f2', 'v19: name byte 4 is the end'),
    (0x005caa78, '00000000', 'a181e254', 'v19: b.ne 0x58faac'),
    (0x005caa7c, '00000000', 'a20b0014', 'v19: b 0x5cd904'),
    (0x005cd904, '00000000', '8a66b852', 'v19: -180.0'),
    (0x005cd908, '00000000', '5301271e', 'v19: fmov s19, w10'),
    (0x005cd90c, '00000000', '4228331e', 'v19: Fade moved 180 down (to the 4:3 bottom edge)'),
    (0x005cd910, '00000000', '13102f1e', 'v19: fmov s19, #1.5'),
    (0x005cd914, '00000000', '2108331e', 'v19: and stretched 1.5x tall: it covers the 4:3 screen'),
    (0x005cd918, '00000000', 'd702ff17', 'v19: no further rule'),
    (0x005cbd24, '00000000', 'aaca8dd2', 'v18: x10 = "UnitPub"'),
    (0x005cbd28, '00000000', '2a8daef2', 'v18: movk x10, #0x7469, lsl #16'),
    (0x005cbd2c, '00000000', '0aaacef2', 'v18: movk x10, #0x7550, lsl #32'),
    (0x005cbd30, '00000000', '4a0ce0f2', 'v18: movk x10, #0x62, lsl #48'),
    (0x005cbd34, '00000000', '7f010aeb', 'v18: cmp x11, x10'),
    (0x005cbd38, '00000000', 'a0ebe154', 'v18: b.eq 0x58faac (UnitPub, the hero art: not stretched)'),
    (0x005cbd3c, '00000000', '5a2a0014', 'v22: b 0x5d66a4 (L_SpotDetail and L_Info checks; v18 had b 0x5a18a4)'),
]

# v20: choice boxes (Common_Choice: MenuItemList holds L_MenuItem00..03 at y 210 / 90 / -30 / -150). The edge rule moved only the
# outer two, so the choices split apart; children of a parent named MenuItem* are now left together (cave 0x5d2564 after v17).
_UI_V20 = [
    (0x005d2564, '00000000', 'aaa98cd2', 'v20: x10 = "MenuItem"'),
    (0x005d2568, '00000000', 'caadaef2', 'v20: movk x10, #0x756e, lsl #16'),
    (0x005d256c, '00000000', '2a89cef2', 'v20: movk x10, #0x7449, lsl #32'),
    (0x005d2570, '00000000', 'aaacedf2', 'v20: movk x10, #0x6d65, lsl #48'),
    (0x005d2574, '00000000', '9f010aeb', 'v20: cmp x12, x10'),
    (0x005d2578, '00000000', 'e0f7dd54', 'v20: children of MenuItem* (choice lists): leave together'),
    (0x005d257c, '00000000', 'cb010014', 'v27: b 0x5d2ca8 (children of L_Info; v20 had b 0x5a6868)'),
]

# v21: the footer key help (Common_Footer: N_Footer > A_KeyHelp at y -520, the talk window's Text Log / Hide UI / Auto-Advance) jumped
# 180 up for a few frames whenever it opened or closed: Footer_In / Footer_Out move N_Footer by y -4, so its parent was off (0,0) and the
# edge rule let go. A parent whose global y is within 4 of 0 now counts as at (0,0) (cave 0x5d3064, from the v15 parent checks' exit).
_UI_V21 = [
    (0x005d3064, '00000000', '0c02261e', 'v21: fmov w12, s16 (parent global y)'),
    (0x005d3068, '00000000', '8c790012', 'v21: and w12, w12, #0x7fffffff (|y|)'),
    (0x005d306c, '00000000', '0a10a852', 'v21: mov w10, #0x40800000 (4.0)'),
    (0x005d3070, '00000000', '9f010a6b', 'v21: cmp w12, w10'),
    (0x005d3074, '00000000', '89c8ce54', 'v21: b.ls 0x570984 (|y| <= 4: edge rule as under (0,0))'),
    (0x005d3078, '00000000', 'ffecfe17', 'v21: b 0x58e474 (others: leave)'),
]

# v22: travel map spot info (Gmap_UI: N_SpotDetail > L_SpotDetail, 2548x1395, holding Gmap_UI_SpotDetail's Bg, N_Img and N_Info at y 540).
# v10's overlay rule stretched L_SpotDetail 4/3 tall and v4's edge rule moved its children, so the info text, the level pills and the ore list
# came out tall and off the top while the dark backdrop (Bg, sized by the game to N_DummyMargin's global y against a hard 540, the 16:9 top
# edge) stopped short and the ore list spilled below it. L_SpotDe* is now left unscaled by the overlay rule (cave 0x5d66a4, after v18's UnitPub
# check), and the backdrop sizing uses 720, the 4:3 top edge (0x168ed78). Checked on the device at Dagsion and Niraga Mine against 16:9.
# v23: quest panels (Common_Quest, Common_QuestTalk: L_Info 1634x1096; Common_TutorialMenu: L_Info 1766x1080). The overlay rule caught them
# as full-screen (>= 1080 tall) and stretched them 4/3, so the quest offer, the Quest List and the tutorials looked tall. A pane named exactly
# L_Info is now left unscaled and moved 180 up, so its top meets the 4:3 top as the list beside it does (caves 0x5d7de4, 0x5d7988; the move
# ends the rules for the pane, as v19's Fade does, or the edge rule would move it again). Checked on the Quest List and the Tutorials.
_UI_V22 = [
    (0x0168ed78, 'e880a852', '8886a852', 'v22: mov w8, #0x44340000 (720.0, the 4:3 top edge, for the spot info backdrop; was 540.0)'),
    (0x005d66a4, '00000000', '8ae98bd2', 'v22: x10 = "L_SpotDe"'),
    (0x005d66a8, '00000000', '6a0aaef2', 'v22: movk x10, #0x7053, lsl #16'),
    (0x005d66ac, '00000000', 'ea8dcef2', 'v22: movk x10, #0x746f, lsl #32'),
    (0x005d66b0, '00000000', '8aa8ecf2', 'v22: movk x10, #0x6544, lsl #48'),
    (0x005d66b4, '00000000', '7f010aeb', 'v22: cmp x11, x10'),
    (0x005d66b8, '00000000', 'a09fdc54', 'v22: b.eq 0x58faac (L_SpotDetail: not stretched)'),
    (0x005d66bc, '00000000', 'ca050014', 'v23: b 0x5d7de4 (L_Info check)'),
    (0x005d7de4, '00000000', '8ae98bd2', 'v23: x10 = "L_Info"'),
    (0x005d7de8, '00000000', '2ac9adf2', 'v23: movk x10, #0x6e49, lsl #16'),
    (0x005d7dec, '00000000', 'caeccdf2', 'v23: movk x10, #0x6f66, lsl #32'),
    (0x005d7df0, '00000000', '7f010aeb', 'v23: cmp x11, x10'),
    (0x005d7df4, '00000000', '80dcfd54', 'v28: b.eq 0x5d3984 (RootPane check; v23 had b.eq 0x5d7988)'),
    (0x005d7df8, '00000000', 'ab78fe17', 'v24: b 0x5760a4 name checks (L_EquipL, N_Pos, MenuItem, Viewport, L_Scroll), then the v12 L_List check at 0x5a18a4; v23 had b 0x5a18a4'),
    (0x005d7988, '00000000', '8a66a852', 'v23: mov w10, #0x43340000 (180.0)'),
    (0x005d798c, '00000000', '5301271e', 'v23: fmov s19, w10'),
    (0x005d7990, '00000000', '4228331e', 'v23: fadd s2, s2, s19 (L_Info: 180 up, not stretched)'),
    (0x005d7994, '00000000', 'b8dafe17', 'v23: b 0x58e474 (no further rule)'),
]

# v24: big panels that are not full-screen layers (found from the romfs layouts, Layout/*.arc, after players' reports on 0.3.22): v10's overlay rule
# (>= 1896x960 or >= 1080 tall under an anchored parent) stretched them 4/3 tall: the item lists (Common_SendUnitItem / Equip_*: L_EquipList*,
# 1770x1132 under the sliding Left anchor: the gift list's top went off screen), the result telops (Common_TlpResult: N_Pos 500x1200, holding Quest
# Complete, class mastered and ability learned), the dialogue choices (Common_Choice: MenuItemList 1920x1080), the dialogue history (Common_TalkLog:
# the 1500x1080 Viewport scissor and its L_ScrollBar). Names starting with L_EquipL, MenuItem, Viewport, L_Scroll and the name N_Pos now skip the
# stretch and keep the other rules (caves 0x5760a4, 0x5b4d04, 0x566484, 0x55fd44, 0x55f444: 7 words each, chained after v23's L_Info check).
# v29: L_UnitInfo 3400x1625 (Common_UnitInfoScout, Battle_UnitInfoDetail) sits under a Left anchor at y 0 while the Right panel beside it (anchor y 446)
# takes the edge move, so the left column stood 180 below the right one at 4:3; it now moves up by the same shape shift (v23's L_Info move, 0x5d7988).
# v26: also L_UnitIn* (Common_UnitInfoScout's L_UnitInfo 3400x1625: Character Info when recruiting, stretched tall; v17 already keeps its children in place),
# cave 0x55a9a4 after the L_Scroll check.
# v35: the result telops (Quest Complete, class mastered, ability learned after training, items acquired) still came out 4/3 tall now and then
# on the phone: Common_TlpResult is built anew for each telop, and its first layout pass can run before N_Pos has its name, so v24's name test
# missed it and the game kept the stretched matrix (the same race as v32 / v34). N_Pos is now told by its layout height, 1200, set when the
# pane is made; no other pane in the game's layouts is 1200 tall (cave 0x5b4d04, same place in the chain).
_UI_V24 = [
    (0x005760a4, '00000000', '8ae98bd2', 'v24: L_EquipL not stretched'),
    (0x005760a8, '00000000', 'aa28aef2', 'v24: movk x10, #0x7145, lsl #16'),
    (0x005760ac, '00000000', 'aa2ecdf2', 'v24: movk x10, #0x6975, lsl #32'),
    (0x005760b0, '00000000', '0a8ee9f2', 'v24: movk x10, #0x4c70, lsl #48'),
    (0x005760b4, '00000000', '7f010aeb', 'v24: cmp x11, x10'),
    (0x005760b8, '00000000', 'a0cf0c54', 'v24: b.eq #0x58faac'),
    (0x005760bc, '00000000', '12fb0014', 'v24: b #0x5b4d04'),
    (0x005b4d04, '00000000', '0aac4079', 'v35: ldrh w10, [x0, #0x56] (top half of the pane height; v24 tested the name N_Pos)'),
    (0x005b4d08, '00000000', '4a114051', 'v35: sub w10, w10, #0x4000'),
    (0x005b4d0c, '00000000', '5f591271', 'v35: cmp w10, #0x496 (height 1200 to 1201.99: Common_TlpResult N_Pos, the only pane that tall)'),
    (0x005b4d10, '00000000', 'e06ced54', 'v35: b.eq 0x58faac (the result telops: not stretched)'),
    (0x005b4d14, '00000000', 'dcc5fe17', 'v35: b 0x566484 (the MenuItem check, as before)'),
    (0x005b4d18, '00000000', '1f2003d5', 'v35: nop'),
    (0x005b4d1c, '00000000', '1f2003d5', 'v35: nop'),
    (0x00566484, '00000000', 'aaa98cd2', 'v24: MenuItem not stretched'),
    (0x00566488, '00000000', 'caadaef2', 'v24: movk x10, #0x756e, lsl #16'),
    (0x0056648c, '00000000', '2a89cef2', 'v24: movk x10, #0x7449, lsl #32'),
    (0x00566490, '00000000', 'aaacedf2', 'v24: movk x10, #0x6d65, lsl #48'),
    (0x00566494, '00000000', '7f010aeb', 'v24: cmp x11, x10'),
    (0x00566498, '00000000', 'a0b01454', 'v24: b.eq #0x58faac'),
    (0x0056649c, '00000000', '2ae6ff17', 'v24: b #0x55fd44'),
    (0x0055fd44, '00000000', 'ca2a8dd2', 'v24: Viewport not stretched'),
    (0x0055fd48, '00000000', 'aaecaef2', 'v24: movk x10, #0x7765, lsl #16'),
    (0x0055fd4c, '00000000', '0aeecdf2', 'v24: movk x10, #0x6f70, lsl #32'),
    (0x0055fd50, '00000000', '4a8eeef2', 'v24: movk x10, #0x7472, lsl #48'),
    (0x0055fd54, '00000000', '7f010aeb', 'v24: cmp x11, x10'),
    (0x0055fd58, '00000000', 'a0ea1754', 'v24: b.eq #0x58faac'),
    (0x0055fd5c, '00000000', 'bafdff17', 'v24: b #0x55f444'),
    (0x0055f444, '00000000', '8ae98bd2', 'v24: L_Scroll not stretched'),
    (0x0055f448, '00000000', '6a6aacf2', 'v24: movk x10, #0x6353, lsl #16'),
    (0x0055f44c, '00000000', '4aeecdf2', 'v24: movk x10, #0x6f72, lsl #32'),
    (0x0055f450, '00000000', '8a8dedf2', 'v24: movk x10, #0x6c6c, lsl #48'),
    (0x0055f454, '00000000', '7f010aeb', 'v24: cmp x11, x10'),
    (0x0055f458, '00000000', 'a0321854', 'v24: b.eq #0x58faac'),
    (0x0055f45c, '00000000', '52edff17', 'v26: b 0x55a9a4 (L_UnitIn check; v24 had b 0x5a18a4)'),
    (0x0055a9a4, '00000000', '8ae98bd2', 'v26: L_UnitIn* (Character Info) not stretched'),
    (0x0055a9a8, '00000000', 'aacaadf2', 'v26: movk x10, #0x6e55, lsl #16'),
    (0x0055a9ac, '00000000', '2a8dcef2', 'v26: movk x10, #0x7469, lsl #32'),
    (0x0055a9b0, '00000000', '2ac9edf2', 'v26: movk x10, #0x6e49, lsl #48'),
    (0x0055a9b4, '00000000', '7f010aeb', 'v26: cmp x11, x10'),
    (0x0055a9b8, '00000000', '807e3e54', 'v29: b.eq #0x5d7988 (L_UnitIn*: not stretched and moved up by the shape shift, as the Right panel beside it; v26 had b.eq 0x58faac)'),
    (0x0055a9bc, '00000000', 'ba1b0114', 'v26: b #0x5a18a4'),
]

# v25: UI placed on a 3D position (the unit type / status icons in battle; any pane the game anchors to a world point). The engine's world-to-screen helper
# (main+0xb81b4c..: the point through the camera, divided by w, then x * 960 + 960, y * 540 + 540 on a 1920x1080 canvas, normalised again for the layout) used the
# 16:9 half-height, but the 4:3 layout is 1440 high and squeezed into the frame, so the icons sat 3/4 as far from the centre as their units (players' report on
# 0.3.22). The y half-height is now 960 x the camera's height / width (the Screen shape cam word: 720 at 4:3, 540 at 16:9), the centre stays 540 (cave 0xb785e4).
_UI_V25 = [
    (0x00b81c00, '0201271e', '79daff17', 'v25: b 0xb785e4 (world-to-screen y: half-height from the shape)'),
    (0x00b785e4, '00000000', '0201271e', 'v25: fmov s2, w8'),
    (0x00b785e8, '00000000', '70d5ec1c', 'v25: ldr s16, #0xb52094'),
    (0x00b785ec, '00000000', '088ea852', 'v25: mov w8, #0x44700000'),
    (0x00b785f0, '00000000', '1101271e', 'v25: fmov s17, w8'),
    (0x00b785f4, '00000000', '100a311e', 'v25: fmul s16, s16, s17'),
    (0x00b785f8, '00000000', '0008101f', 'v25: fmadd s0, s0, s16, s2'),
    (0x00b785fc, '00000000', '83250014', 'v25: b #0xb81c08'),
]

# v27: quest turn-in window (Common_QuestTalk > L_Info > Common_QuestInfo's N_Body, holding the quote, Objective and Reward). v23 moves L_Info 180 up and
# ends its rules; its children are not edge-moved while L_Info's global y is 180, but on a frame where that move was not yet in the parent's global matrix
# they took v4's edge move too and kept it: now and then the contents sat 180 higher than the box, the quest title off the top (seen on the Nova in one of
# four openings of the same turn-in, never at 16:9). Children of a parent named exactly L_Info now stay in place (cave 0x5d2ca8, after v20's MenuItem check).
_UI_V27 = [
    (0x005d2ca8, '00000000', '8ae98bd2', 'v27: children of a parent named exactly L_Info stay in place'),
    (0x005d2cac, '00000000', '2ac9adf2', 'v27: movk x10, #0x6e49, lsl #16'),
    (0x005d2cb0, '00000000', 'caeccdf2', 'v27: movk x10, #0x6f66, lsl #32'),
    (0x005d2cb4, '00000000', '9f010aeb', 'v27: cmp x12, x10'),
    (0x005d2cb8, '00000000', 'e0bddd54', 'v27: b.eq #0x58e474'),
    (0x005d2cbc, '00000000', 'eb4eff17', 'v27: b #0x5a6868'),
]

# v28: the quest turn-in and offer window (Common_QuestTalk) has its L_Info right under RootPane, with its Report / Don't Report buttons (N_Menu >
# MenuItemList, y -459) laid out just below it; the Quest List and the Tutorials have theirs under a Right anchor beside a list. v23's 180 up move
# suits the list screens but left an empty band between the turn-in window and its buttons. An L_Info whose parent's name starts with Root now keeps its 16:9 place
# (unscaled, no further rule: cave 0x5d3984 before v23's move at 0x5d7988), and so does the window's frame (Wdw, 1014x882 at y 452 under RootPane,
# which v4's edge rule moved 180 up: a top-level Wdw about 1014 wide, caves 0x5e7684 and 0x5ec244 at the edge move itself, 0x58e464,
# which three rule paths reach, so no frame of the opening slips past it; the Base Menu's Wdw is 520 wide).
# The whole window then sits where 16:9 has it, with the buttons right under it. Checked on the Nova at the Behelda Axes turn-in.
# v34: the frame is now told by its type (Window pane vtable) and layout place (y 452), not its name or width, which the game had not set yet
# on the first layout pass of some openings (a heap dump showed the frame at y 632 = 452 + 180, contents in place). v33 used y alone: on some openings the width was not 1014 yet when the frame was first
# laid out, so it took the edge move and kept it (the frame 180 above the contents, an empty band at its bottom).
# v29: the L_Info test is now "parent named Right*" (the Quest List and the Tutorials) instead of "parent named Root*": on some openings (after
# Don't Report and talking again) the quest window's L_Info had another parent name, took v23's move and its contents sat 180 above the frame.
_UI_V28 = [
    (0x005d3984, '00000000', '2c5940f9', 'v28: ldr x12, [x9, #0xb0] (parent name; x9 is the parent on the overlay path)'),
    (0x005d3988, '00000000', '4a2a8d52', 'v29: w10 = "Righ"'),
    (0x005d398c, '00000000', 'ea0cad72', 'v29: movk w10, #0x6867, lsl #16'),
    (0x005d3990, '00000000', '9f010a6b', 'v29: cmp w12, w10'),
    (0x005d3994, '00000000', '0157dd54', 'v29: b.ne #0x58e474 (L_Info not under a Right anchor, e.g. the quest window: in place, not stretched)'),
    (0x005d3998, '00000000', 'fc0f0014', 'v29: b #0x5d7988 (L_Info beside a list, under Right: v23\'s move up by the shape shift)'),
    (0x005e7684, '00000000', '0a0040f9', 'v34: the pane vtable (from the edge move at 0x58e464, which every path to it passes)'),
    (0x005e7688, '00000000', '0dcf00f0', 'v34: x13 = the ui2d Window pane vtable (main+0x1fca0a0)'),
    (0x005e768c, '00000000', 'ad810291', 'v34: add x13, x13, #0xa0'),
    (0x005e7690, '00000000', '5f010deb', 'v34: cmp x10, x13'),
    (0x005e7694, '00000000', 'e15d0254', 'v34: b.ne 0x5ec250 (not a window: the move)'),
    (0x005e7698, '00000000', '0a6c4079', 'v34: ldrh w10, [x0, #0x36] (top half of its layout y)'),
    (0x005e769c, '00000000', 'ea120014', 'v34: b 0x5ec244'),
    (0x005ec244, '00000000', '4a114051', 'v34: sub w10, w10, #0x4000'),
    (0x005ec248, '00000000', '5f890f71', 'v34: cmp w10, #0x3e2 (y 452 to 454: QuestTalk Wdw, the only window there)'),
    (0x005ec24c, '00000000', '4011d154', 'v34: b.eq 0x58e474 (the turn-in window frame stays in place)'),
    (0x005ec250, '00000000', '3342211e', 'v34: fneg s19, s17 (the move, as before)'),
    (0x005ec254, '00000000', '8588fe17', 'v34: b 0x58e468'),
]

# v32 (replaces v30 and v31): the quest window's contents could come out 4/3 tall and 180 too high on an opening (now and then on the Nova,
# never on the PC). Heap dumps of that state (DM_CTL memdump) showed L_Info with global y scale 4/3 and N_Body at 4/3 x (396 + 180): the overlay
# stretch and the edge move, which the L_Info name checks block, so a layout pass ran while the part was built and before it had that name
# (v31's "RootPane with a parent" test did not catch it either); the game then keeps those matrices until the window is rebuilt. The checks now
# use the pane's type (its vtable: the ui2d Parts pane, main+0x1fc9398) and size, which are set when the pane is made:
# - a Parts pane is never stretched by the overlay rule (cave 0x60ee84 at the stretch, 0x5a3c8c; the big parts the rule met are all exempt
#   by name already: L_List, L_EquipList*, L_UnitInfo, L_Info);
# - nothing below a Parts pane at least 1080 tall and under 1896 wide (the quest window, Quest List and Tutorials' L_Info) gets a rule, and
#   nothing below a RootPane that has a parent (caves 0x5a2b44, 0x5fbb64, 0x6037c4, 0x609a64, 0x60bb84, 0x60c8e4, walking pane +0x18 parents).
# L_Info itself keeps its own treatment by name (v23 / v29 move up under a Right anchor).
_UI_V30 = [
    (0x005a2b44, '00000000', 'ec0300aa', 'v32: x12 = the pane (walk the pane and its ancestors)'),
    (0x005a2b48, '00000000', '2ed100f0', 'v32: x14 = the ui2d Parts pane vtable (main+0x1fc9398)'),
    (0x005a2b4c, '00000000', 'ce610e91', 'v32: add x14, x14, #0x398'),
    (0x005a2b50, '00000000', '1f2003d5', 'v32: nop '),
    (0x005a2b54, '00000000', '4fea8dd2', 'v32: x15 = "RootPane"'),
    (0x005a2b58, '00000000', 'ef8daef2', 'v32: movk x15, #0x746f, lsl #16'),
    (0x005a2b5c, '00000000', '02640114', 'v32: b #0x5fbb64'),
    (0x005fbb64, '00000000', '0f2accf2', 'v32: movk x15, #0x6150, lsl #32'),
    (0x005fbb68, '00000000', 'cfadecf2', 'v32: movk x15, #0x656e, lsl #48'),
    (0x005fbb6c, '00000000', '8d5940f9', 'v32: loop: x13 = name'),
    (0x005fbb70, '00000000', 'bf010feb', 'v32: cmp x13, x15'),
    (0x005fbb74, '00000000', '80f70654', 'v32: b.eq 0x609a64 (a RootPane: has it a parent?)'),
    (0x005fbb78, '00000000', '131f0014', 'v32: b #0x6037c4'),
    (0x006037c4, '00000000', '9f0100eb', 'v32: the pane itself is not tested as a big part'),
    (0x006037c8, '00000000', '60000054', 'v32: b.eq #0x6037d4'),
    (0x006037cc, '00000000', 'ee200014', 'v32: b 0x60bb84 (a big part above?)'),
    (0x006037d0, '00000000', '1f2003d5', 'v32: nop '),
    (0x006037d4, '00000000', '8c0d40f9', 'v32: next: its parent'),
    (0x006037d8, '00000000', '6c5bc1b4', 'v32: cbz x12, 0x586344 (top reached: the rules as before)'),
    (0x006037dc, '00000000', 'e4e0ff17', 'v32: b #0x5fbb6c'),
    (0x00609a64, '00000000', '8a0d40f9', 'v32: the RootPane\'s parent'),
    (0x00609a68, '00000000', '6a50c2b5', 'v32: cbnz x10, 0x58e474 (a RootPane with a parent is a part being built: no rule)'),
    (0x00609a6c, '00000000', '56e7ff17', 'v32: b #0x6037c4'),
    (0x0060bb84, '00000000', '8a0140f9', 'v32: ancestor vtable'),
    (0x0060bb88, '00000000', '5f010eeb', 'v32: cmp x10, x14'),
    (0x0060bb8c, '00000000', '41e2fb54', 'v32: b.ne 0x6037d4 (not a part)'),
    (0x0060bb90, '00000000', '8d5540b9', 'v32: its height'),
    (0x0060bb94, '00000000', 'ea90a852', 'v32: mov w10, #0x44870000 (1080.0)'),
    (0x0060bb98, '00000000', 'bf010a6b', 'v32: cmp w13, w10'),
    (0x0060bb9c, '00000000', '52030014', 'v32: b #0x60c8e4'),
    (0x0060c8e4, '00000000', '8377fb54', 'v32: b.lo 0x6037d4 (under 1080 tall)'),
    (0x0060c8e8, '00000000', '8d5140b9', 'v32: its width'),
    (0x0060c8ec, '00000000', 'aa9da852', 'v32: mov w10, #0x44ed0000 (1896.0)'),
    (0x0060c8f0, '00000000', 'bf010a6b', 'v32: cmp w13, w10'),
    (0x0060c8f4, '00000000', '0277fb54', 'v32: b.hs 0x6037d4 (full width, e.g. L_UnitInfo 3400)'),
    (0x0060c8f8, '00000000', 'df06fe17', 'v32: b 0x58e474 (inside a big panel part, e.g. L_Info 1634x1096: no rule)'),
    (0x0060ee84, '00000000', '0d0040f9', 'v32: the pane vtable (from the overlay stretch, 0x5a3c8c)'),
    (0x0060ee88, '00000000', 'cecd00f0', 'v32: x14 = the Parts pane vtable (main+0x1fc9398)'),
    (0x0060ee8c, '00000000', 'ce610e91', 'v32: add x14, x14, #0x398'),
    (0x0060ee90, '00000000', 'bf010eeb', 'v32: cmp x13, x14'),
    (0x0060ee94, '00000000', 'c060c054', 'v32: b.eq 0x58faac (a Parts pane is never stretched; the other rules as before)'),
    (0x0060ee98, '00000000', '6dc0fd17', 'v32: b 0x57f04c (the stretch)'),
]

# Screen shape (Game settings › Aspect ratio › Screen shape): every value above that depends on the 4:3 shape is read from one of seven words instead of being part of an
# instruction, so the host can lay the UI out for any shape from 1:1 to 16:9 by writing those words at load (game.tsv shape_table, loader.c shape_apply). The words hold the
# 4:3 values, so the variant is the 4:3 mod as before when nothing writes them (4:3 itself, or a host without shape_apply). Each site's fmov / mov becomes an `ldr` of its
# word (one instruction, any value); the words are zero padding after a ret, out of the rule chains. Checked on a PC emulator at 1:1, 5:4 (generated only), 4:3, 7:5, 3:2
# and 16:10: title, world map, World Map menu, tutorials, a map battle's forecast and combat (1:1) lay out against the picture's edges as the 4:3 mod does.
#   cam      0xb52094  the 3D camera's height / width (0xb51e38; 4:3 0.75)
#   squeeze  0x55f5b8  the UI projection's y row and the scissor's y (0x55f618, 0x574568, 0x59c550; 4:3 0.75 = shape x 9/16)
#   shift    0x560328  the edge rule's move and L_Info's (0x58e5c4, 0x5d7988; 4:3 180 = (1920 / shape - 1080) / 2)
#   nshift   0x560398  the obelisk Fade's move (0x5cd904; 4:3 -180)
#   fade     0x560598  the obelisk Fade's y scale (0x5cd910; 4:3 1.5 = 1 + shift / 360)
#   top      0x168ee28 the travel map backdrop's top edge (0x168ed78; 4:3 720 = 960 / shape)
#   stretch  0x5605a8  the overlay rule's y scale (0x5a3c88, with 0x57f04c a nop; 4:3 4/3 = 1920 / shape / 1080)
_SHAPE_WORDS = {'cam': 0xb52094, 'squeeze': 0x55f5b8, 'shift': 0x560328, 'nshift': 0x560398, 'fade': 0x560598, 'top': 0x168ee28, 'stretch': 0x5605a8}


def _ldr(rt, pc, lit, base):   # ldr s<rt> (base 0x1c000000) / w<rt> (0x18000000), <literal at lit>
    return (base | ((((lit - pc) // 4) & 0x7ffff) << 5) | rt).to_bytes(4, 'little').hex()


def _shape(cuts):
    import struct
    t, s, w = _SHAPE_WORDS, 0x1c000000, 0x18000000
    new = {0xb51e38: _ldr(1, 0xb51e38, t['cam'], s), 0x55f618: _ldr(27, 0x55f618, t['squeeze'], s), 0x574568: _ldr(1, 0x574568, t['squeeze'], s),
           0x59c550: _ldr(21, 0x59c550, t['squeeze'], s), 0x58e5c4: _ldr(10, 0x58e5c4, t['shift'], w), 0x5d7988: _ldr(10, 0x5d7988, t['shift'], w),
           0x5cd904: _ldr(10, 0x5cd904, t['nshift'], w), 0x5cd910: _ldr(19, 0x5cd910, t['fade'], s), 0x168ed78: _ldr(8, 0x168ed78, t['top'], w),
           0x5a3c88: _ldr(10, 0x5a3c88, t['stretch'], w), 0x57f04c: '1f2003d5'}
    out = [(o, orig, new[o], why + ' (Screen shape: its value from _SHAPE_WORDS)') if o in new else (o, orig, nw, why) for o, orig, nw, why in cuts]
    assert len({c[0] for c in out} & set(new)) == len(new)
    vals = {'cam': 0.75, 'squeeze': 0.75, 'shift': 180.0, 'nshift': -180.0, 'fade': 1.5, 'top': 720.0, 'stretch': 4 / 3}
    return out + [(t[k], '00000000', struct.pack('<f', vals[k]).hex(), f'Screen shape table: {k} (4:3 {vals[k]:g})') for k in t]


# v36: storing an item when the inventory is full (Common_SendUnitItem: "Select an item to put in storage", after a chest or a drop in battle).
# Its unit header L_UnitInfo (y 396) sits right above the item list L_EquipList (y 214), both under the root. The list took the edge move,
# 180 up to the 4:3 top edge, but v11 exempts every pane named L_UnitIn* from the rules (for the unit details screens), so the header stayed
# and the list's top rows slid under it. A pane named L_UnitIn* at layout y 396 (only this one, in all the game's layouts) now takes the rules
# as any pane does, so header and list move up together; every other L_UnitIn* keeps v11's exemption (cave 0x58f448, from 0x58c948).
_UI_V36 = [
    (0x0058f448, '00000000', '0a6c4079', 'v36: ldrh w10, [x0, #0x36] (top half of its layout y)'),
    (0x0058f44c, '00000000', '4a114051', 'v36: sub w10, w10, #0x4000'),
    (0x0058f450, '00000000', '5f190f71', 'v36: cmp w10, #0x3c6 (y 396 to 397.99: Common_SendUnitItem L_UnitInfo)'),
    (0x0058f454, '00000000', '8ae98bd2', 'v36: mov x10, #0x5f4c ("L_", as the name chain had it)'),
    (0x0058f458, '00000000', 'a0a7fe54', 'v36: b.eq 0x58c94c (the item storage header: on through the rules)'),
    (0x0058f45c, '00000000', '06fcff17', 'v36: b 0x58e474 (other L_UnitIn*: no rules, as v11)'),
]


_MAIN = 'db93b0125f4850601d61c3edde012f8e'
VARIANT_CUTS = {'43': {_MAIN: _shape(_V11 + _SCISSOR43 + _UI_V12 + _UI_V13 + _UI_V14 + _UI_V15 + _UI_V16 + _UI_V17 + _UI_V18 + _UI_V20 + _UI_V21 + _UI_V22 + _UI_V24 + _UI_V25 + _UI_V27 + _UI_V28 + _UI_V30 + _UI_V36)}}

BINDING = [
    {'what': "Fire Emblem Fortune's Weave native 4:3 variant (VARIANT_CUTS['43']: camera aspect and ui2d pane rules)", 'now': 'build', 'goal': 'unreviewed', 'purpose': 'rendering',
     'why': 'an opt-in variant (Game settings › Aspect ratio) of about 230 words in code caves of this main; each ui2d rule names panes of this build\'s layouts'},
]
