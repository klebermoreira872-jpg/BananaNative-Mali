// nxoodle: the game's own Oodle (or LZ5) decoder on the phone, for packing on a PC that cannot run it (Windows, Linux x86-64): the DM_OODLE_SERVE tool mode of the host
// (dm/host/hle_oodle.c) as an executable for adb shell, pushed beside libnxhost.so as nxreplay is. Run with the rewritten modules' folder, as the Mac host is:
//   DM_OODLE_SERVE=1 LD_LIBRARY_PATH=. ./nxoodle <modules dir>
// Requests come on stdin and answers go to stdout in shader_split.py oodle_ask's protocol ({u64 compressed length, u64 raw length} + bytes → {u64 decoded length} + bytes);
// the log stays on stderr. The host serves from the guest's main thread before the SDK starts (dm_oodle_serve_maybe exits when stdin ends), so nothing of the game runs
// and no window is needed. dm/tools/oodle_adb.py is the PC side (DM_OODLE_HOST points at it): stdin / stdout are then a TCP socket handed over by toybox nc.
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
int nxhost_main(int argc, char **argv);   // front_android.c: heap tagging off, then the host's main (bound inside libnxhost.so by -Bsymbolic, not to this one)
int main(int argc, char **argv) {
    if (!getenv("DM_OODLE_SERVE")) { fprintf(stderr, "nxoodle: set DM_OODLE_SERVE=1 (this is only the decoder tool mode)\n"); return 2; }
    if (argc < 2) { fprintf(stderr, "usage: DM_OODLE_SERVE=1 nxoodle <modules dir>\n"); return 2; }
    // An answer is two writes (the length, then the bytes). On a socket, Nagle holds the second until the first is acknowledged, and the PC delays that acknowledgement
    // (up to 200 ms on Windows): one stall per request, about all of the time a pack spends decoding. No delay on the answer socket (a pipe ignores this)
    int one = 1; setsockopt(1, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
    return nxhost_main(argc, argv);
}