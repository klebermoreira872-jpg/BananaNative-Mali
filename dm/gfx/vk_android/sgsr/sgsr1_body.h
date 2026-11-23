//============================================================================================================
//
//
//                  Copyright (c) 2025, Qualcomm Innovation Center, Inc. All rights reserved.
//                              SPDX-License-Identifier: BSD-3-Clause
//
//============================================================================================================
// Snapdragon Game Super Resolution 1 (SGSR 1), shared by the neural upscaler's compute pass (ndsr_sgsr.comp) and the present's fragment pass (present_sgsr.frag).
// Ported from Qualcomm's sgsr/v1/include/glsl/sgsr1_shader_mobile_edge_direction.frag (https://github.com/SnapdragonStudios/snapdragon-gsr, d926f074), under its licence:
//
// Copyright (c) 2023, Qualcomm Innovation Center, Inc. All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice,
//    this list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its contributors
//    may be used to endorse or promote products derived from this software
//    without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
//
// SPDX-License-Identifier: BSD-3-Clause
//============================================================================================================
// The body of Qualcomm's main, included inside the includer's own main (a function call around it changes the compute pass's precision decorations, so its SPIR-V stays as it was):
// in: highp vec2 in_TEXCOORD0 (the output pixel's centre in the input texture's 0..1 coordinates), highp vec4 ViewportInfo[1] (1 / input width, 1 / input height, width, height);
// out: vec4 color, whose xyz is the result. Qualcomm's configuration and the changes from its fragment shader are listed in ndsr_sgsr.comp

	vec4 color;
	if(OperationMode == 1)
		color.xyz = textureLod(ps0,in_TEXCOORD0.xy,0.0).xyz;
	else
		color.xyzw = textureLod(ps0,in_TEXCOORD0.xy,0.0).xyzw;

	if ( OperationMode!=4)
	{
		highp vec2 imgCoord = ((in_TEXCOORD0.xy*ViewportInfo[0].zw)+vec2(-0.5,0.5));
		highp vec2 imgCoordPixel = floor(imgCoord);
		highp vec2 coord = (imgCoordPixel*ViewportInfo[0].xy);
		vec2 pl = (imgCoord+(-imgCoordPixel));
		vec4  left = textureGather(ps0,coord, OperationMode);

		float edgeVote = abs(left.z - left.y) + abs(color[OperationMode] - left.y)  + abs(color[OperationMode] - left.z) ;
		if(edgeVote > EdgeThreshold)
		{
			coord.x += ViewportInfo[0].x;

			vec4 right = textureGather(ps0,coord + vec2(ViewportInfo[0].x, 0.0), OperationMode);
			vec4 upDown;
			upDown.xy = textureGather(ps0,coord + vec2(0.0, -ViewportInfo[0].y),OperationMode).wz;
			upDown.zw  = textureGather(ps0,coord+ vec2(0.0, ViewportInfo[0].y), OperationMode).yx;

			float mean = (left.y+left.z+right.x+right.w)*0.25;
			left = left - vec4(mean);
			right = right - vec4(mean);
			upDown = upDown - vec4(mean);
			color.w =color[OperationMode] - mean;

			float sum = (((((abs(left.x)+abs(left.y))+abs(left.z))+abs(left.w))+(((abs(right.x)+abs(right.y))+abs(right.z))+abs(right.w)))+(((abs(upDown.x)+abs(upDown.y))+abs(upDown.z))+abs(upDown.w)));
			float sumMean = 1.014185e+01/sum;
			float std = (sumMean*sumMean);

#if defined(UseEdgeDirection)
			vec3 data = vec3(std, edgeDirection(left, right));
#else
			float data = std;
#endif
			vec2 aWY = weightY(pl.x, pl.y+1.0, upDown.x,data);
			aWY += weightY(pl.x-1.0, pl.y+1.0, upDown.y,data);
			aWY += weightY(pl.x-1.0, pl.y-2.0, upDown.z,data);
			aWY += weightY(pl.x, pl.y-2.0, upDown.w,data);
			aWY += weightY(pl.x+1.0, pl.y-1.0, left.x,data);
			aWY += weightY(pl.x, pl.y-1.0, left.y,data);
			aWY += weightY(pl.x, pl.y, left.z,data);
			aWY += weightY(pl.x+1.0, pl.y, left.w,data);
			aWY += weightY(pl.x-1.0, pl.y-1.0, right.x,data);
			aWY += weightY(pl.x-2.0, pl.y-1.0, right.y,data);
			aWY += weightY(pl.x-2.0, pl.y, right.z,data);
			aWY += weightY(pl.x-1.0, pl.y, right.w,data);

			float finalY = aWY.y/aWY.x;
			float maxY = max(max(left.y,left.z),max(right.x,right.w));
			float minY = min(min(left.y,left.z),min(right.x,right.w));
			float deltaY = clamp(EdgeSharpness*finalY, minY, maxY) -color.w;

			//smooth high contrast input
			deltaY = clamp(deltaY, -23.0 / 255.0, 23.0 / 255.0);

			color.x = max((color.x+deltaY),0.0);   // (Qualcomm: clamp(..., 0.0, 1.0); see above)
			color.y = max((color.y+deltaY),0.0);
			color.z = max((color.z+deltaY),0.0);
		}
	}

