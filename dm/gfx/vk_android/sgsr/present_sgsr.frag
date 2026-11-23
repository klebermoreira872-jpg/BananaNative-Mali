#version 450
#extension GL_GOOGLE_include_directive : require
// Qualcomm's Snapdragon Game Super Resolution 1 scaling the window to the screen (vka_present.c, DM_VK_PRESENT_SCALE=sgsr1): one pass straight into the swapchain image,
// one output pixel per fragment, with the filter of the neural upscaler's SGSR 1 (sgsr1.h and sgsr1_body.h, BSD-3-Clause, Qualcomm Innovation Center: the licence is in
// them and in android/NOTICE.md) and its configuration. A fragment pass and not ndsr_sgsr.comp's SPIR-V: that one stores into a B10G11R11 storage image (or packed words), while
// the present draws into the swapchain's RGBA8 / BGRA8 image, which need not allow storage use, inside the letterbox and turned for pre-rotation (present_uv.h). The UNORM
// store clamps the result to 0..1 as Qualcomm's own shader does
layout(location = 0) out vec4 o;
#include "../present/present_uv.h"

precision mediump float;
precision highp int;

layout(set = 0, binding = 0) uniform mediump sampler2D ps0;

#include "sgsr1.h"

void main()
{
	highp vec4 ViewportInfo[1]; ViewportInfo[0] = pc.tex;
	highp vec2 in_TEXCOORD0 = present_uv();

#include "sgsr1_body.h"

	o = vec4(color.xyz, 1.0);
}
