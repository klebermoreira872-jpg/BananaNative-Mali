#!/bin/sh
# Builds BananaNative-<version>-aarch64.AppImage on an x86_64 or arm64 machine with Docker (the cross image of linux/build.sh):
#   linux/appimage/build-appimage.sh [title ID ...]      default: every host already built in linux/build/, else Mario Kart World
# One host binary per game goes in (the game profile is compiled into the host, as on Android). Output: linux/build/appimage/
# Downloads appimagetool (x86_64) and the aarch64 AppImage runtime from the AppImage project's GitHub releases on first use, and fontTools from PyPI.
# The pins: a version and the sha256 GitHub lists for the asset on its release page (a cached file is checked again on every run, a download before use).
APPIMAGETOOL_VERSION=1.9.1
APPIMAGETOOL_SHA256=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
RUNTIME_VERSION=20251108   # (github.com/AppImage/type2-runtime: runtime-aarch64)
RUNTIME_SHA256=00cbdfcf917cc6c0ff6d3347d59e0ca1f7f45a6df1a428a0d6d8a78664d87444
FONTTOOLS_VERSION=4.67.0   # (as .github/requirements/lint.txt; a wheel, not hash-checked)
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd); HERE="$ROOT/linux/appimage"; OUT="$ROOT/linux/build/appimage"; APPDIR="$OUT/AppDir"; TOOLS="$OUT/tools"
IDS="$*"
[ -n "$IDS" ] || IDS=$(ls "$ROOT/linux/build" 2>/dev/null | grep -E '^[0-9A-F]{16}$' | tr '\n' ' ')
[ -n "$IDS" ] || IDS=0400C3F00006E000
VER=$(git -C "$ROOT" describe --tags --always 2>/dev/null | sed 's/^v//'); VER=${VER:-dev}

rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/sdl3" "$TOOLS"
for id in $IDS; do
  echo "== host $id"; "$ROOT/linux/build.sh" "$id" | tail -1
  cp "$ROOT/linux/build/$id/nxhost_$id" "$APPDIR/usr/bin/"
done
[ -f "$ROOT/linux/build/sdl3/out/lib/libSDL3.so.0" ] || "$ROOT/linux/build-sdl3.sh"   # (the fallback SDL3 the AppImage carries, used only where the system has none)
cp -L "$ROOT/linux/build/sdl3/out/lib/libSDL3.so.0" "$APPDIR/usr/lib/sdl3/"
cp "$HERE/AppRun" "$APPDIR/AppRun"; chmod +x "$APPDIR/AppRun"
cp "$HERE/banananative.desktop" "$APPDIR/"
rsvg-convert -w 256 -h 256 "$ROOT/android/images/logo.svg" -o "$APPDIR/banananative.png"
cp "$ROOT/LICENSE" "$APPDIR/" 2>/dev/null || true
cp "$ROOT/linux/README.md" "$APPDIR/README.md"
mkdir -p "$APPDIR/usr/share/banananative"; cp "$ROOT/linux/tools/banananative-governor" "$ROOT/linux/tools/install-governor-helper.sh" "$APPDIR/usr/share/banananative/"
# the source it was built from, for the launcher's "Prepare a game" (it downloads that exact tree for the packer): NX_SOURCE_URL is a repository on
# git.eden-emu.dev (Forgejo: <url>/archive/<commit>.tar.gz) that has the commit
printf 'commit %s\nurl %s\nversion %s\nchain %s\nabi %s\n' "$(git -C "$ROOT" rev-parse HEAD)" "${NX_SOURCE_URL:-https://git.eden-emu.dev/moceure/BananaNative}" "$VER" \
  "$(sed -n 's/^#define DMSH_VK_CHAIN "\([0-9a-f]*\)".*/\1/p' "$ROOT/dm/gfx/nvn/dmsh_chain_vk.h")" \
  "$(sed -n 's/^#define DMSH_VK_ABI "\([0-9a-f]*\)".*/\1/p' "$ROOT/dm/gfx/nvn/dmsh_chain_vk.h")" > "$APPDIR/usr/share/banananative/source"
# the known transitions of the shader library (android/SHADERS.md, "Known transitions"), as the APK carries its chain's rows: the launcher shows a pack whose
# library is of a row's older version as ready (the host plays a library of another version with its ABI), not as one to prepare again
cp "$ROOT/dm/gfx/vk_android/vka_known_transitions.tsv" "$APPDIR/usr/share/banananative/known_transitions.tsv"
cp "$HERE/launcher.py" "$HERE/steam_shortcut.py" "$APPDIR/usr/share/banananative/"
# The shared-font stand-ins, as the APK carries them (GameFonts.java, build.gradle nxExtFont): Noto Sans as standard.ttf and the button icons' nintendo_ext.ttf
# (dm/tools/make_ext_font.py, letters from the same Noto Sans; fontTools in a Python environment of its own under tools/). AppRun sets DM_FONT_DIR to them
F="$APPDIR/usr/share/banananative/fonts"; mkdir -p "$F"
cp "$ROOT/dm/third_party/fonts/NotoSans-Regular-subset.ttf" "$F/standard.ttf"; cp "$ROOT/dm/third_party/fonts/OFL.txt" "$F/OFL.txt"
{ [ -x "$TOOLS/pyenv/bin/python" ] || python3 -m venv "$TOOLS/pyenv"; } && "$TOOLS/pyenv/bin/python" -m pip -q install --only-binary :all: "fonttools==$FONTTOOLS_VERSION" || true
"$TOOLS/pyenv/bin/python" "$ROOT/dm/tools/make_ext_font.py" "$F/nintendo_ext.ttf" "$ROOT/dm/third_party/fonts/NotoSans-Regular-subset.ttf" >/dev/null ||
  { rm -f "$F/nintendo_ext.ttf"; echo "[RED] nintendo_ext.ttf not made (fontTools): button icons in game text will be drawn as '?'"; }

# appimagetool runs here (x86_64); the runtime put in front of the image is the aarch64 one
sha256() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi < "$1" | cut -d' ' -f1; }
# fetch <url> <file> <sha256>: a cached file that is not the pin is deleted and downloaded again; the download goes to <file>.part and is renamed only
# when its sha256 is the pin, else the script stops (exit, not set -e)
fetch() {
  if [ -f "$2" ]; then [ "$(sha256 "$2")" = "$3" ] && return; echo "$(basename "$2"): not the pinned file, downloading it again"; rm -f "$2"; fi
  rm -f "$2.part"; curl -fsSL -o "$2.part" "$1" || { rm -f "$2.part"; echo "[RED] $1: download failed"; exit 1; }
  got=$(sha256 "$2.part"); [ "$got" = "$3" ] || { rm -f "$2.part"; echo "[RED] $(basename "$2"): sha256 $got, expected $3"; exit 1; }
  mv "$2.part" "$2"
}
AIT="$TOOLS/appimagetool-$APPIMAGETOOL_VERSION"; RT="$TOOLS/runtime-aarch64-$RUNTIME_VERSION"
fetch "https://github.com/AppImage/appimagetool/releases/download/$APPIMAGETOOL_VERSION/appimagetool-x86_64.AppImage" "$AIT" "$APPIMAGETOOL_SHA256"; chmod +x "$AIT"
fetch "https://github.com/AppImage/type2-runtime/releases/download/$RUNTIME_VERSION/runtime-aarch64" "$RT" "$RUNTIME_SHA256"
IMG="$OUT/BananaNative-$VER-aarch64.AppImage"
ARCH=aarch64 "$AIT" --appimage-extract-and-run --no-appstream --runtime-file "$RT" "$APPDIR" "$IMG" 2>&1 | tail -3
ls -la "$IMG"
