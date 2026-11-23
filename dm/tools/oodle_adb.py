#!/usr/bin/env python3
"""DM_OODLE_HOST for a PC that cannot run the game's own decoder (Windows, Linux x86-64): the game's OodleLZ_Decompress runs on an arm64 Android phone instead, in nxoodle
(android/host/nxoodle.c, the host's DM_OODLE_SERVE tool mode). The packer starts this as it would start the Mac host, as `DM_OODLE_HOST <modules dir>` (shader_split.py
oodle_ask, uepak.py OodleHost), and talks the same protocol on stdin / stdout: {u64 compressed length, u64 raw length} + bytes in, {u64 decoded length} + bytes out.

How the bytes travel: adb starts the phone's toybox nc listening on a port, nc runs nxoodle on the connection, and this connects to it over the network (adb over
Wi-Fi: the phone's address from the serial, or DM_OODLE_ADB_NET) or through adb forward (a phone on USB, or DM_OODLE_ADB_FORWARD=1). Not through adb's stdin: adb on
Windows reads stdin as text and ends it at the first 0x1A byte, and adb exec-out does not forward stdin at all.

Requests are independent, so each one is kept until its whole answer is back: a connection that stalls (Wi-Fi drops packets, adb forward stops reading) or ends is
dropped, a fresh nxoodle is started, and the request is sent again (DM_OODLE_ADB_TIMEOUT seconds per answer, default 15; the first answer of a connection also waits
for nxoodle to load the modules). A decoder that dies on the same request twice in a row is the game's decoder refusing it: the bridge ends, and the packer reports it.

Once per game, on the phone (`oodle_adb.py push` does it):
  /data/local/tmp/nxoodle/libnxhost.so, nxoodle   built with -DGAME=<base title ID> (cmake --build <build> --target nxoodle)
  /data/local/tmp/nxoodle/<name>/                 the rewritten modules (the pack's *.patched.bin, *.key, *.tsv: what the packer passes as DM_OODLE_MODULES)

Environment: DM_OODLE_ADB (adb, default "adb"), DM_OODLE_ADB_SERIAL (else ANDROID_SERIAL), DM_OODLE_ADB_DIR (default /data/local/tmp/nxoodle), DM_OODLE_ADB_MODULES (the
modules folder on the phone; default <DM_OODLE_ADB_DIR>/<the local folder's name>), DM_OODLE_ADB_TRACE (a folder for a per-bridge trace). nxoodle's log goes to
<DM_OODLE_ADB_DIR>/logs/<port>.log on the phone."""
import os, posixpath, re, shlex, socket, struct, subprocess, sys, time

def adb_base():
    adb = os.environ.get('DM_OODLE_ADB', 'adb')
    serial = os.environ.get('DM_OODLE_ADB_SERIAL') or os.environ.get('ANDROID_SERIAL')
    return [adb] + (['-s', serial] if serial else [])

def phone_dir(): return os.environ.get('DM_OODLE_ADB_DIR', '/data/local/tmp/nxoodle')

def phone_address():
    if os.environ.get('DM_OODLE_ADB_FORWARD') == '1': return None
    serial = os.environ.get('DM_OODLE_ADB_SERIAL') or os.environ.get('ANDROID_SERIAL') or ''
    m = re.fullmatch(r'(\d+\.\d+\.\d+\.\d+):\d+', serial)
    return os.environ.get('DM_OODLE_ADB_NET') or (m.group(1) if m else None)

def read_exact(f, n):   # from a file (stdin); b'' only at a clean end before the first byte
    b = bytearray()
    while len(b) < n:
        k = f.read(n - len(b))
        if not k:
            if not b: return b''
            raise EOFError('stdin ended inside a request')
        b += k
    return bytes(b)

def recv_exact(s, n):
    b = bytearray()
    while len(b) < n:
        k = s.recv(min(n - len(b), 1 << 20))
        if not k: raise EOFError('nxoodle closed the connection')
        b += k
    return bytes(b)

class Decoder:
    """One nxoodle on the phone, on its own port, reached over the network or adb forward."""
    def __init__(self, mods, port, tr):
        self.port, self.tr, self.host = port, tr, phone_address()
        d = phone_dir()
        if not self.host:
            self.host = '127.0.0.1'
            subprocess.check_call(adb_base() + ['forward', 'tcp:%d' % port, 'tcp:%d' % port], stdout=subprocess.DEVNULL)
        # nc runs the command on the connection: it first says R (so a connection made before nc listened is seen as dead), then becomes nxoodle
        cmd = 'cd %s && mkdir -p logs && DM_OODLE_SERVE=1 LD_LIBRARY_PATH=. exec nc -l -p %d sh -c %s %s 2>logs/%d.log' % (
            shlex.quote(d), port, shlex.quote('printf R; exec ./nxoodle "$0"'), shlex.quote(mods), port)
        self.server = subprocess.Popen(adb_base() + ['shell', cmd], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.s, self.fresh = None, True
        for _ in range(80):
            if self.server.poll() is not None: break
            time.sleep(0.25)
            try: s = socket.create_connection((self.host, port), timeout=5)
            except OSError: continue
            s.settimeout(3)
            try: r = s.recv(1)
            except OSError: r = b''
            if r == b'R': s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1); self.s = s; break
            s.close()
        if not self.s: self.close(); raise ConnectionError('nxoodle did not come up on port %d (see %s/logs/%d.log on the phone)' % (port, d, port))
        tr('decoder up', self.host, port)

    def ask(self, req, timeout):
        self.s.settimeout(timeout + (30 if self.fresh else 0))   # the first answer also waits for nxoodle to load the modules
        t0 = time.perf_counter()
        self.s.sendall(req)
        head = recv_exact(self.s, 8)
        t1 = time.perf_counter()
        self.fresh = False
        got = struct.unpack('<Q', head)[0]
        body = recv_exact(self.s, got) if got else b''
        t2 = time.perf_counter()
        self.nreq = getattr(self, 'nreq', 0) + 1; self.tsum = getattr(self, 'tsum', 0.0) + (t2 - t0)
        if t2 - t0 > 0.1: self.tr('slow %.0f ms (head %.0f) %d -> %d' % ((t2 - t0) * 1e3, (t1 - t0) * 1e3, len(req) - 16, got))
        if self.nreq % 500 == 0: self.tr('%d requests, avg %.1f ms' % (self.nreq, self.tsum / self.nreq * 1e3))
        return head + body

    def close(self, clean=False):
        if self.s:
            try:
                if clean: self.s.shutdown(socket.SHUT_WR)   # nxoodle sees the end of its input and exits
            except OSError: pass
            self.s.close(); self.s = None
        try: self.server.wait(10 if clean else 0.1)
        except subprocess.TimeoutExpired: self.server.kill()
        if self.host == '127.0.0.1': subprocess.call(adb_base() + ['forward', '--remove', 'tcp:%d' % self.port], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def serve(local_modules):
    mods = os.environ.get('DM_OODLE_ADB_MODULES') or posixpath.join(phone_dir(), os.path.basename(os.path.normpath(local_modules)))
    timeout = float(os.environ.get('DM_OODLE_ADB_TIMEOUT', '15'))
    tdir = os.environ.get('DM_OODLE_ADB_TRACE')
    tf = open(os.path.join(tdir, '%d.txt' % os.getpid()), 'a', buffering=1) if tdir else None
    def tr(*a):
        if tf: tf.write('%.3f %s\n' % (time.time(), ' '.join(map(str, a))))
    src, out = sys.stdin.buffer, sys.stdout.buffer
    base, k, dec, n, retries = 30000 + (os.getpid() * 7) % 19000, 0, None, 0, 0
    while True:
        head = read_exact(src, 16)
        if not head: break
        req = head + read_exact(src, struct.unpack('<QQ', head)[0])
        deaths = 0
        while True:
            try:
                if dec is None: dec = Decoder(mods, base + k % 900, tr); k += 1
                ans = dec.ask(req, timeout)
                break
            except (OSError, EOFError, ConnectionError) as e:
                stalled = isinstance(e, socket.timeout)
                tr('request', n, 'lost:', type(e).__name__, e)
                retries += 1
                if dec: dec.close()
                dec = None
                if not stalled:
                    deaths += 1
                    if deaths >= 2: sys.stderr.write('oodle_adb: nxoodle ended twice on request %d (%d → %d bytes): the decoder refuses it\n' % (n, len(req) - 16, struct.unpack('<QQ', head)[1])); return 1
                if retries > 200: sys.stderr.write('oodle_adb: too many lost answers (%d); is the phone still reachable?\n' % retries); return 1
        out.write(ans); out.flush(); n += 1
    tr('done', n, 'requests', retries, 'retried')
    if dec: dec.close(clean=True)
    return 0

def push(build, local_modules, name):
    d = phone_dir(); mods = posixpath.join(d, name)
    subprocess.check_call(adb_base() + ['shell', 'mkdir -p %s' % shlex.quote(mods)])
    subprocess.check_call(adb_base() + ['push', os.path.join(build, 'libnxhost.so'), os.path.join(build, 'nxoodle'), d + '/'])
    subprocess.check_call(adb_base() + ['push', os.path.join(local_modules, '.'), mods + '/'])
    subprocess.check_call(adb_base() + ['shell', 'chmod 755 %s/nxoodle' % shlex.quote(d)])

if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'push':
        if len(sys.argv) != 5: sys.exit('usage: oodle_adb.py push <build dir> <local modules dir> <name on the phone>')
        push(*sys.argv[2:5])
    elif len(sys.argv) >= 2: sys.exit(serve(sys.argv[1]))
    else: sys.exit('usage: oodle_adb.py <modules dir>   (as DM_OODLE_HOST)   |   oodle_adb.py push <build dir> <modules dir> <name>')