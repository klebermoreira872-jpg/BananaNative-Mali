package dev.nxnative.android;

/** RunGuard on the JVM, driven by dm/tools/tests/test_android_gametask.py: prints "ok &lt;n&gt;" when every check holds, else the first failure (exit 1) */
public final class RunGuardJvmTest {
    private static int n;

    private static void check(boolean ok, String what) {
        if (!ok) { System.out.println("FAIL " + what); System.exit(1); }
        n++;
    }

    public static void main(String[] a) {
        check(!RunGuard.otherRunning(false, null, "0100000000010000"), "no host: a start");
        check(!RunGuard.otherRunning(false, "0100000000010000", "0100000000020000"), "a host that is not running: a start");
        check(!RunGuard.otherRunning(true, "0100000000010000", "0100000000010000"), "the same game: attach");
        check(RunGuard.otherRunning(true, "0100000000010000", "0100000000020000"), "another game while one runs: stop it first");
        check(RunGuard.otherRunning(true, "0100000000010000", null), "an intent without a title while one runs: the running game");
        check(!RunGuard.otherRunning(true, null, "0100000000020000"), "running but no title known: as before");
        check(RunGuard.endsProcess(true, false), "finished: the process ends");
        check(!RunGuard.endsProcess(true, true), "finished for a configuration change: recreated");
        check(!RunGuard.endsProcess(false, false), "destroyed, not finished (Don't keep activities): recreated, the game runs on");
        System.out.println("ok " + n);
    }
}
