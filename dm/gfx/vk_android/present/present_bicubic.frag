#version 450
#extension GL_GOOGLE_include_directive : require
// Bicubic scaling of the window to the screen (vka_present.c, DM_VK_PRESENT_SCALE=bicubic): one pass straight into the swapchain image, one output pixel per fragment.
// The kernel is Catmull-Rom (the cubic convolution with a = -0.5): it passes through the source pixels, so edges and HUD text keep the sharpness the picture has, where a
// B-spline (smoother, no overshoot) blurs more than bilinear filtering at the 1.5-2x scales of a phone screen. Its 4x4 footprint is read with 9 bilinear fetches instead
// of 16 point reads: along each axis the two middle weights are both positive, so one bilinear fetch between the middle pixels, placed at w2 / (w1 + w2), returns their
// weighted sum (w1 + w2 >= 1, the outer weights are negative and small). The outer taps' overshoot is clamped by the UNORM store
layout(set = 0, binding = 0) uniform sampler2D tex;
layout(location = 0) out vec4 o;
#include "present_uv.h"

// The four weights of a pixel at fraction f past the second of four (each component one axis)
void weights(vec2 f, out vec2 w0, out vec2 w1, out vec2 w2, out vec2 w3) {
    vec2 f2 = f * f, f3 = f2 * f;
    w0 = 0.5 * (-f3 + 2.0 * f2 - f);
    w1 = 0.5 * (3.0 * f3 - 5.0 * f2) + 1.0;
    w2 = 0.5 * (-3.0 * f3 + 4.0 * f2 + f);
    w3 = 0.5 * (f3 - f2);
}

void main() {
    vec2 p = present_uv() * pc.tex.zw;          // in pixels
    vec2 c1 = floor(p - 0.5) + 0.5;              // the centre of the second of the four pixels on each axis
    vec2 w0, w1, w2, w3;
    weights(p - c1, w0, w1, w2, w3);
    vec2 wm = w1 + w2;
    vec2 a = (c1 - 1.0) * pc.tex.xy, m = (c1 + w2 / wm) * pc.tex.xy, b = (c1 + 2.0) * pc.tex.xy;   // the three fetch places per axis
    vec3 r = (textureLod(tex, vec2(a.x, a.y), 0.0).rgb * w0.x + textureLod(tex, vec2(m.x, a.y), 0.0).rgb * wm.x + textureLod(tex, vec2(b.x, a.y), 0.0).rgb * w3.x) * w0.y
           + (textureLod(tex, vec2(a.x, m.y), 0.0).rgb * w0.x + textureLod(tex, vec2(m.x, m.y), 0.0).rgb * wm.x + textureLod(tex, vec2(b.x, m.y), 0.0).rgb * w3.x) * wm.y
           + (textureLod(tex, vec2(a.x, b.y), 0.0).rgb * w0.x + textureLod(tex, vec2(m.x, b.y), 0.0).rgb * wm.x + textureLod(tex, vec2(b.x, b.y), 0.0).rgb * w3.x) * w3.y;
    o = vec4(r, 1.0);
}
