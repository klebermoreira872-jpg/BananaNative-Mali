# Sourced by linux/build.sh and linux/build-sdl3.sh, with ROOT set to the repository. NX_IMG: the cross image (NX_CROSS_IMAGE, else nx-linux-cross:24.04),
# built from linux/Dockerfile when it is missing. nx_run '<command>': runs it in that image with the repository at /src. Rootless Docker maps the caller to the
# container's root, so there the container runs as root (its files are the caller's; -u <uid>:<gid> could not write to /src); otherwise it runs as the caller
NX_IMG=${NX_CROSS_IMAGE:-nx-linux-cross:24.04}
docker image inspect "$NX_IMG" >/dev/null 2>&1 || docker build -q -t "$NX_IMG" "$ROOT/linux" >/dev/null
if docker info -f '{{.SecurityOptions}}' 2>/dev/null | grep -q rootless; then NX_USER=0:0; else NX_USER=$(id -u):$(id -g); fi
nx_run() { docker run --rm -u "$NX_USER" -v "$ROOT":/src -w /src "$NX_IMG" sh -c "$1"; }
