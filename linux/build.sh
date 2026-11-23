#!/bin/sh
# Cross build of nxhost for aarch64 Linux on an x86_64 or arm64 machine with Docker: linux/build.sh <base game title ID> [ninja arguments]
# → linux/build/<title ID>/nxhost_<title ID>. The image (linux/Dockerfile, NX_CROSS_IMAGE to use another) is built on first use. SDL3: linux/sysroot
# (include/SDL3 and lib/libSDL3.so copied from the target system) when it is there, else SDL3 built from source (linux/build-sdl3.sh)
set -e
GAME=${1:?usage: linux/build.sh <base game title ID>}; shift
ROOT=$(cd "$(dirname "$0")/.." && pwd); . "$ROOT/linux/common.sh"
SYS=linux/sysroot
if [ ! -f "$ROOT/$SYS/include/SDL3/SDL.h" ]; then
  [ -f "$ROOT/linux/build/sdl3/out/include/SDL3/SDL.h" ] || "$ROOT/linux/build-sdl3.sh" >/dev/null
  SYS=linux/build/sdl3/out
fi
nx_run "cmake -S linux/host -B linux/build/$GAME -G Ninja -DCMAKE_TOOLCHAIN_FILE=/src/linux/host/aarch64-clang.cmake -DGAME=$GAME -DNX_SYSROOT=/src/$SYS >/dev/null && ninja -C linux/build/$GAME $*"
