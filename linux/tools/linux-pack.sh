#!/bin/sh
# Prepares a game pack on aarch64 (or x86_64) Linux with the same packer the Android app and the Mac use (scripts/pack_android.py):
# the code rewrite (Python, Capstone 5, lz4, zbic) and the Vulkan shader library (the translator's portable .NET dlls under the .NET 10
# runtime, SPIRV-Tools' spirv-val). Everything it installs stays in one folder, no root needed.
#   linux/tools/linux-pack.sh setup                     once: <env>/venv (Python packages), <env>/dotnet (.NET 10 runtime), the translator wrapper
#   linux/tools/linux-pack.sh lib                       optional, once per source tree: the translator as a library, so shaders use every core
#   linux/tools/linux-pack.sh <game.nup or dump folder> [pack_android.py options]
#                                                       the pack goes to <title ID>-work/android-pack beside the game file (the launcher's
#                                                       picker finds it under ~/Games); shaders take minutes (Mario Kart World: 11,603)
# NX_PACK_ENV: the environment folder (default ~/.local/share/banananative/packer). Needs python3 (3.12+; 3.14 builds the shader library without
# backports.zstd), curl, spirv-val on PATH (Ubuntu/Debian: spirv-tools) and a checkout of this repository (this script's own).
# The pins setup downloads, each checked against its hash before use (bump: the version and the hash from pypi.org/pypi/pip/<version>/json, the same tag
# of github.com/pypa/get-pip, and the runtime's linux tar.gz in builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json). The Python
# packages are exact versions, wheels only, not hash-checked.
PIP_VERSION=26.3   # (only where the system Python has no ensurepip: get-pip.py installs this wheel, with no index)
PIP_URL=https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/pip-26.3-py3-none-any.whl
PIP_SHA256=f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13
GETPIP_URL=https://raw.githubusercontent.com/pypa/get-pip/26.3/public/get-pip.py
GETPIP_SHA256=f7654c5589318e1d0789575b2586ce76937eb9943602adda8b15b3be3aa0dac3
PACKAGES="capstone==5.0.9 lz4==4.4.5 zbic==1.0.1.post1"
DOTNET_VERSION=10.0.15   # (the runtime, glibc only: Microsoft's linux-arm64 and linux-x64 archives)
DOTNET_ARM64_SHA512=e2e8b907d9eb6c239cccf5c1fe67fd9a72c56fddccedca9ba41c8a53ff034293b335fdd9f7ab504f09bf7b3f165e0d14e34fc9ea1f06cc0e86d0dfb06d274b6a
DOTNET_X64_SHA512=a90177d75bc891f71aa814dde3bcf76a356f5a506824669f1891754457954a3d13b72f3ca04c98fa0fe588514a5a781f8a87b17930ee802105c14f9edb28318a
# lib: the .NET 10 SDK that compiles the translator library (the same releases.json, the release of the runtime above), and clang to link it
DOTNET_SDK_VERSION=10.0.404
DOTNET_SDK_ARM64_SHA512=3533a3869da219cac45c567aadac3d8e96cdf1c6a04fe1c1d5fdeefea5d45af8424488f0144730d11b4a751f7ad546fb11e4c2b2725cd8401efee726711f8f11
DOTNET_SDK_X64_SHA512=577d0eb17fec33d029104c5c63a1ab0accc3e28776274abef2218dbac5af18d2109b5406d26b31d76f5c245215e3ba0926a94c20246c672c41847c9e1eb1dc50
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ENV=${NX_PACK_ENV:-${XDG_DATA_HOME:-$HOME/.local/share}/banananative/packer}
XBIN="$ROOT/dm/gfx/tools/dmsh_xlate_bin"
WRAP="$XBIN/dmsh_xlate-linux"   # (beside the dlls: vk_android_build.py checks the dlls next to the translator it is given)

# The CPU's .NET name: arm64 or x64
rid() {
  case $(uname -m) in
    aarch64|arm64) echo arm64 ;;
    x86_64) echo x64 ;;
    *) echo "[RED] $(uname -m): there is no pinned .NET for this CPU" >&2; exit 1 ;;
  esac
}

# fetch <url> <file> <256|512> <hash>: the download goes to <file>.part and is renamed only when its hash is the pin, else it is deleted and the
# script stops (exit, not set -e: setup also runs from a || list)
digest() { if command -v "sha$1sum" >/dev/null; then "sha$1sum"; else shasum -a "$1"; fi | cut -d' ' -f1; }
fetch() {
  rm -f "$2.part"; curl -fsSL --retry 3 -o "$2.part" "$1" || { rm -f "$2.part"; echo "[RED] $1: download failed"; exit 1; }
  got=$(digest "$3" < "$2.part"); [ "$got" = "$4" ] || { rm -f "$2.part"; echo "[RED] $(basename "$2"): sha$3 $got, expected $4"; exit 1; }
  mv "$2.part" "$2"
}

setup() {
  mkdir -p "$ENV"
  if [ ! -x "$ENV/venv/bin/python" ]; then
    python3 -m venv "$ENV/venv" 2>/dev/null || {   # (no ensurepip, as on Ubuntu without python3-venv: the pinned pip wheel through its bootstrap script)
      rm -rf "$ENV/venv" "$ENV/pip"; mkdir -p "$ENV/pip"
      fetch "$GETPIP_URL" "$ENV/get-pip.py" 256 "$GETPIP_SHA256"
      fetch "$PIP_URL" "$ENV/pip/pip-$PIP_VERSION-py3-none-any.whl" 256 "$PIP_SHA256"
      python3 -m venv --without-pip "$ENV/venv"
      "$ENV/venv/bin/python" "$ENV/get-pip.py" -q --no-index --find-links "$ENV/pip" "pip==$PIP_VERSION" || { rm -rf "$ENV/venv"; exit 1; }; }
  fi
  "$ENV/venv/bin/python" -m pip -q install --only-binary :all: $PACKAGES
  if [ ! -x "$ENV/dotnet/dotnet" ] || ! "$ENV/dotnet/dotnet" --list-runtimes | grep -q '^Microsoft.NETCore.App 10\.'; then
    a=$(rid); [ $a = arm64 ] && h=$DOTNET_ARM64_SHA512 || h=$DOTNET_X64_SHA512
    # (ldd names musl on musl systems; /lib/ld-musl-* only counts without ldd, as glibc systems can have musl installed beside)
    if (ldd --version 2>&1 || true) | grep -qi musl || { ! command -v ldd >/dev/null && ls /lib/ld-musl-* >/dev/null 2>&1; }; then
      echo "[RED] musl is not supported by the pinned .NET runtime"; exit 1
    fi
    fetch "https://builds.dotnet.microsoft.com/dotnet/Runtime/$DOTNET_VERSION/dotnet-runtime-$DOTNET_VERSION-linux-$a.tar.gz" "$ENV/dotnet.tar.gz" 512 "$h"
    rm -rf "$ENV/dotnet.part"; mkdir "$ENV/dotnet.part"; tar -xzf "$ENV/dotnet.tar.gz" -C "$ENV/dotnet.part"; rm -f "$ENV/dotnet.tar.gz"
    [ -x "$ENV/dotnet.part/dotnet" ] || { rm -rf "$ENV/dotnet.part"; echo "[RED] the .NET archive has no dotnet at its root"; exit 1; }
    rm -rf "$ENV/dotnet"; mv "$ENV/dotnet.part" "$ENV/dotnet"
  fi
  printf '#!/bin/sh\n# The shader translator on Linux (linux/tools/linux-pack.sh): the portable dlls beside this script under the .NET 10 runtime\nexec "${DOTNET_ROOT:-%s}/dotnet" "$(dirname "$0")/dmsh_xlate.dll" "$@"\n' "$ENV/dotnet" > "$WRAP"
  chmod +x "$WRAP"
  command -v spirv-val >/dev/null || echo "[RED] spirv-val is not on PATH: install SPIRV-Tools (Ubuntu/Debian: sudo apt install spirv-tools) before packing shaders"
  echo "translator: $("$WRAP" --source-sha) (the tree expects $(cd "$ROOT/dm/gfx/tools" && "$ENV/venv/bin/python" -c 'from dmsh_chain import xlate_source_sha as s; print(s() if callable(s) else s)'))"
  echo "ready: $ENV"
}

# The translator library (lib) and SPIRV-Tools' shared library let the shader build run its Python half (each shader's SPIR-V rewrites, which hold the
# GIL) in DMSH_VK_PROCS sub-interpreters of its own process, one per core, as the phone's Prepare does: a sub-interpreter may not start programs, so with
# the translator and spirv-val as programs the build keeps one interpreter, and its threads share one core (docs/reference/packing.md, "The Linux
# packer's shader build runs on about one core"). The library is NativeAOT, from the phone's project (dm/gfx/tools/dmsh_xlate_android, Program.cs
# unchanged) with this machine's runtime identifier, in <env>/xlate/<source tree digest>/: vk_android_build.py checks the digest it embeds against
# the tree, so a new tree needs `lib` again (until then the packer uses the wrapper). The SDK stays in <env>/sdk; the NuGet packages are checked against
# linux/tools/xlate-nuget.sha512 before they are used
TREE=$(cd "$ROOT/dm/gfx/tools" && python3 xlate_tree.py 2>/dev/null) || TREE=
XLIB="$ENV/xlate/$TREE/libdmsh_xlate.so"
# SPIRV-Tools' shared library: SPIRV_VAL when it names one (a build of its own: Debian and Ubuntu package only the programs), else the system's
spirv_lib() { case "$SPIRV_VAL" in *.so|*.so.*) [ -f "$SPIRV_VAL" ] && { echo "$SPIRV_VAL"; return; } ;; esac; { ldconfig -p 2>/dev/null | awk '/libSPIRV-Tools-shared\.so /{print $NF; exit}'; ls /usr/lib64/libSPIRV-Tools-shared.so /usr/lib/libSPIRV-Tools-shared.so /usr/lib/*-linux-gnu/libSPIRV-Tools-shared.so 2>/dev/null; } | head -1; }
lib() {
  [ -n "$TREE" ] || { echo "[RED] dm/gfx/tools/xlate_tree.py gave no digest"; exit 1; }
  command -v clang >/dev/null || { echo "[RED] clang is not on PATH: the library is linked with it (Ubuntu/Debian: sudo apt install clang)"; exit 1; }
  a=$(rid); [ $a = arm64 ] && h=$DOTNET_SDK_ARM64_SHA512 || h=$DOTNET_SDK_X64_SHA512
  mkdir -p "$ENV"
  if [ ! -x "$ENV/sdk/dotnet" ] || ! "$ENV/sdk/dotnet" --list-sdks | grep -q "^$DOTNET_SDK_VERSION "; then
    fetch "https://builds.dotnet.microsoft.com/dotnet/Sdk/$DOTNET_SDK_VERSION/dotnet-sdk-$DOTNET_SDK_VERSION-linux-$a.tar.gz" "$ENV/sdk.tar.gz" 512 "$h"
    rm -rf "$ENV/sdk.part"; mkdir "$ENV/sdk.part"; tar -xzf "$ENV/sdk.tar.gz" -C "$ENV/sdk.part"; rm -f "$ENV/sdk.tar.gz"
    rm -rf "$ENV/sdk"; mv "$ENV/sdk.part" "$ENV/sdk"
  fi
  P="$ROOT/dm/gfx/tools/dmsh_xlate_android"; O="$ENV/xlate/$TREE"; N="$ENV/nuget.part"
  mkdir -p "$P/obj" && printf '%s\n' "$TREE" > "$P/obj/tree.sha"   # (embedded as the library's --tree-sha, as build.sh does)
  rm -rf "$O.part" "$N"
  # The NuGet packages (the NativeAOT compiler, the runtime packs, the project's own) are restored into an empty folder first, which runs none of them,
  # and each is checked against linux/tools/xlate-nuget.sha512 before anything is built from them
  dn() { DOTNET_ROOT="$ENV/sdk" NUGET_PACKAGES="$N" DOTNET_CLI_HOME="$ENV" DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 "$ENV/sdk/dotnet" "$@" \
    "$P/dmsh_xlate_android.csproj" -nologo -v quiet -r "linux-$a" -p:RuntimeIdentifier="linux-$a" -p:PublishAotUsingRuntimePack=false \
    -p:DisableUnsupportedError=false -p:NativeLib=Shared -p:OutputType=Library; }
  dn restore || { rm -rf "$N"; echo "[RED] the translator library's NuGet packages did not restore"; exit 1; }
  bad=$(find "$N" -name '*.nupkg.sha512' | while read -r f; do
    r=${f#"$N"/}; id=${r%%/*}; v=${r#*/}; v=${v%%/*}
    awk -F'\t' -v i="$id" -v v="$v" -v h="$(cat "$f")" '$1 == i && $2 == v && $3 == h {ok = 1} END {exit !ok}' "$ROOT/linux/tools/xlate-nuget.sha512" ||
      echo "$id $v"
  done)
  [ -z "$bad" ] || { rm -rf "$N"; echo "[RED] NuGet packages not in linux/tools/xlate-nuget.sha512 or with another sha512, nothing built:" $bad; exit 1; }
  dn publish --no-restore -c Release -o "$O.part" ||
    { rm -rf "$O.part" "$N"; echo "[RED] the translator library did not build: the packer goes on with the wrapper"; exit 1; }
  rm -rf "$N"
  mv "$O.part/dmsh_xlate.so" "$O.part/libdmsh_xlate.so"; rm -f "$O.part/dmsh_xlate.so.dbg"
  rm -rf "$O"; mv "$O.part" "$O"
  [ -n "$(spirv_lib)" ] || echo "[RED] SPIRV-Tools' libSPIRV-Tools-shared.so is not found: the packer keeps one core until it is (Fedora: spirv-tools-libs; Debian and Ubuntu package none: build SPIRV-Tools and name the library in SPIRV_VAL)"
  echo "translator library: $XLIB"
}

case "$1" in
  setup) setup ;;
  lib) lib ;;
  ""|-h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) [ -x "$ENV/venv/bin/python" ] && [ -x "$WRAP" ] || setup
     SV=$(spirv_lib)
     if [ -n "$TREE" ] && [ -f "$XLIB" ] && [ -n "$SV" ]; then
       n=$(nproc 2>/dev/null || echo 4); [ "$n" -gt 12 ] && n=12   # (measured up to 12)
       echo "shader build: the translator and SPIRV-Tools libraries, ${DMSH_VK_PROCS:-$n} worker interpreters"
       DMSH_VK_PROCS=${DMSH_VK_PROCS:-$n} DMSH_VK_XLATE_J=${DMSH_VK_XLATE_J:-$n} XLATE="$XLIB" SPIRV_VAL="$SV" \
         exec "$ENV/venv/bin/python" "$ROOT/scripts/pack_android.py" "$@"
     fi
     echo "shader build: the translator program, on about one core for its Python half (linux/tools/linux-pack.sh lib: one per core)"
     DOTNET_ROOT="$ENV/dotnet" XLATE="$WRAP" exec "$ENV/venv/bin/python" "$ROOT/scripts/pack_android.py" "$@" ;;
esac
