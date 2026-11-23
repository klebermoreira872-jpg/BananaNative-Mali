// SPDX-License-Identifier: GPL-3.0-or-later
// Native 4:3 UI layout rules for Pokemon Pokopia v2.0.1 (kg175 port from analysis/lite3 + analysis/kgshape145).
// Pure portable C so macOS and host unit tests compile alongside the Android host.
#pragma once
#include <stdint.h>

// Pre-bake gate (main+0x1f84fac, OBS 30|4<<8): decides y scale and additive offset for pane p under scaleobj so.
// Saves (so, orig_sx, orig_sy) in a per-thread so-keyed stack, writes so+0x14 = o.sy and so+0x1c = o.add
// (and so+0x10 for T193 cover layers). Invariant: main+0x1f84fb0 bl 0x1f85000 is non-recursive in main
// (only two loop callers at 0x1f84f34 and 0x1f84fb0; pane_bake never re-enters 0x1f84de0), and the TLS stack
// protects against any unexpected nesting on distinct or repeated scaleobjs.
void pkp_ui43_pre_bake(void *so, void *p);

// Post-bake gate (main+0x1f84fb4, OBS 30|5<<8): restores so+0x10, so+0x14 and clears so+0x1c to 0.0f.
void pkp_ui43_post_bake(void *so);

// Global-matrix join gate (main+0x1f72270, OBS 30|3<<8): fixes Pause 1b16778d cursor root children (T183-T187).
void pkp_ui43_gmx_fix(uint64_t *r);
