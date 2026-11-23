// The present's one-pass scalers (vka_present.c scale_copy: present_bicubic.frag, ../sgsr/present_sgsr.frag): a fragment of the swapchain image to the texture coordinate
// of its picture pixel's centre. The swapchain pixel q is turned back to the picture's pixel by q.x * m.xy + q.y * m.zw + t, as RCAS does (the letterbox corner, and for a
// pre-rotated swapchain the quarter or half turn); uv maps that pixel's centre into the window texture's 0..1 coordinates (the crop's scale and corner, the rows read from
// the bottom for a lower-left origin); tex = 1 / texture width, 1 / texture height, width, height. 64 bytes: the FSR passes' push constant range
layout(push_constant) uniform P { ivec4 m; ivec2 t; vec2 pad; vec4 uv; vec4 tex; } pc;
vec2 present_uv() {
    ivec2 q = ivec2(gl_FragCoord.xy);
    return (vec2(q.x * pc.m.xy + q.y * pc.m.zw + pc.t) + 0.5) * pc.uv.xy + pc.uv.zw;
}
