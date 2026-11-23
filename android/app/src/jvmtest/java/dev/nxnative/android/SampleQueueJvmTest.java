package dev.nxnative.android;

import java.util.Arrays;

/** SampleQueue on the JVM, driven by dm/tools/tests/test_android_samplequeue.py: every rule below is checked in place, "ok" on the last line when all hold, an AssertionError otherwise */
public final class SampleQueueJvmTest {
    private static void check(boolean ok, String what) { if (!ok) throw new AssertionError(what); }

    public static void main(String[] a) {
        // enqueue dedupes (waiting, running, tried, skipped), order is first come first served
        SampleQueue q = new SampleQueue();
        check(q.enqueue("A") && q.enqueue("B") && q.enqueue("C"), "three enqueued");
        check(!q.enqueue("A") && !q.enqueue(null), "a waiting pack is not queued twice");
        check(q.order().equals(Arrays.asList("A", "B", "C")), "order");
        check(q.ahead("A") == 0 && q.ahead("C") == 2, "ahead with none running");
        check("A".equals(q.startNext()) && q.startNext() == null, "one check at a time");
        check(!q.enqueue("A"), "the running pack is not queued again");
        check(q.ahead("B") == 1 && q.ahead("C") == 2 && q.ahead("A") == -1, "ahead counts the running one");
        check(q.isRunning("A") && q.active("A") && q.active("B") && !q.active("Z"), "active");

        // tried only after a check ran and ended; the lock being busy marks nothing
        check(!q.startFailed("A", false) && !q.tried("A"), "a refused start (busy) is not a try");
        check(q.running() == null && "A".equals(q.order().get(0)), "the refused one is back at the front");
        check("A".equals(q.startNext()), "tried again");
        for (int i = 0; i < SampleQueue.MAX_START_FAILURES - 1; i++) { check(!q.startFailed("A", true), "failure " + i + " does not give up"); check("A".equals(q.startNext()), "restart"); }
        check(q.startFailed("A", true) && q.tried("A") && !q.active("A"), "given up after N failures to start: tried");
        check(!q.enqueue("A"), "a tried pack is not asked again");
        check("B".equals(q.startNext()), "the next goes on");
        q.ended("B");
        check(q.tried("B") && q.running() == null && !q.enqueue("B"), "ended with a verdict: tried");

        // playTakesLead: the running check stops and waits at the front; nothing marked
        q = new SampleQueue();
        q.enqueue("A"); q.enqueue("B"); q.enqueue("C");
        check(q.playTakesLead() == null, "nothing runs, nothing to stop");
        q.startNext();
        check("A".equals(q.playTakesLead()), "the running check is the one to stop");
        check(q.running() == null && !q.tried("A") && q.order().equals(Arrays.asList("A", "B", "C")), "re-queued at the front, not tried");
        q.startNext(); q.ended("A"); q.startNext();
        check("B".equals(q.running()), "B runs");
        check("B".equals(q.playTakesLead()) && q.order().equals(Arrays.asList("B", "C")), "B back at the front");

        // cancel: leaves, never asked again, the queue goes on
        q = new SampleQueue();
        q.enqueue("A"); q.enqueue("B"); q.enqueue("C");
        check(!q.cancel("B") && !q.active("B") && q.cancelled("B") && !q.enqueue("B"), "a waiting pack is skipped");
        q.startNext();
        check(q.cancel("A") && q.running() == null && !q.tried("A") && q.cancelled("A"), "the running one is skipped: the caller stops it");
        check("C".equals(q.startNext()), "the queue goes on with C");

        // pause / resume
        q = new SampleQueue();
        q.enqueue("A");
        q.pause();
        check(q.startNext() == null && q.paused() && q.any(), "paused: nothing starts");
        q.resume();
        check("A".equals(q.startNext()), "resumed");

        // the signature changes with every card's state
        q = new SampleQueue();
        String s0 = q.signature();
        q.enqueue("A"); String s1 = q.signature();
        q.startNext(); String s2 = q.signature();
        check(!s0.equals(s1) && !s1.equals(s2) && !s0.equals(s2), "signature");

        // when a check may start
        long s = SampleQueue.SETTLE_MS;
        check(SampleQueue.holdReason(s, false, false, true, 100, 0) == null, "may start");
        check(SampleQueue.holdReason(s - 1, false, false, true, 100, 0) != null, "the app has just started");
        check(SampleQueue.holdReason(s, true, false, true, 100, 0) != null, "a game runs");
        check(SampleQueue.holdReason(s, false, true, true, 100, 0) != null, "the packer is busy");
        check(SampleQueue.holdReason(s, false, false, false, 100, 0) != null, "not calm");
        check(SampleQueue.holdReason(s, false, false, true, 100, 101) != null, "cooling");

        // the card's words
        check(SampleQueue.waitingText(0).equals("Waiting to check shaders (next)"), "next");
        check(SampleQueue.waitingText(3).equals("Waiting to check shaders (3 ahead)"), "ahead text");
        check(SampleQueue.runningText(null).equals("Checking shaders…"), "no progress yet");
        SampleQueue.Progress p = SampleQueue.parse("{\"phase\": \"translate\", \"done\": 120, \"total\": 400}\n");
        check(p != null && p.done == 120 && p.total == 400 && SampleQueue.TRANSLATE.equals(p.phase), "progress.json");
        check(SampleQueue.runningText(p).equals("Checking shaders · translating 120 of 400"), "translate text");
        check(SampleQueue.parse("{}") == null && SampleQueue.parse(null) == null && SampleQueue.parse("{\"phase\": \"x\"}") == null, "bad json");
        SampleQueue.Progress sd = SampleQueue.parseSeedLine("seed 12 400");
        check(sd != null && SampleQueue.SEED.equals(sd.phase) && SampleQueue.parseSeedLine("seed: stopped") == null && SampleQueue.parseSeedLine("progress 1 2") == null, "seed line");
        check(SampleQueue.runningText(sd).equals("Checking shaders · reading the game's files 12 of 400"), "seed text");
        check(SampleQueue.bar(null) == 0 && SampleQueue.bar(new SampleQueue.Progress("seed", 0, 0)) == 0, "bar unknown");
        check(SampleQueue.bar(new SampleQueue.Progress("seed", 400, 400)) == 200 && SampleQueue.bar(new SampleQueue.Progress("translate", 0, 400)) == 200
                && SampleQueue.bar(new SampleQueue.Progress("translate", 400, 400)) == 1000 && SampleQueue.bar(new SampleQueue.Progress("translate", 999, 400)) == 1000, "bar is monotone over the phases, capped");
        // startNext(ready): a held pack keeps its place, the next ready one runs
        q = new SampleQueue();
        q.enqueue("A"); q.enqueue("B"); q.enqueue("C");
        check("B".equals(q.startNext(k -> !k.equals("A"))) && q.order().equals(Arrays.asList("B", "A", "C")), "A is held, B runs, A keeps the front of the line");
        q.ended("B");
        check(q.startNext(k -> false) == null && q.running() == null && q.order().equals(Arrays.asList("A", "C")), "none ready: nothing starts");
        check("A".equals(q.startNext()), "ready again: A first");

        // resume words
        check(SampleQueue.runningText(null, true).equals("Resuming shader check…"), "resuming, no progress yet");
        SampleQueue.Progress pr = SampleQueue.parse("{\"phase\": \"translate\", \"done\": 150, \"total\": 300, \"reused\": 120}");
        check(pr != null && pr.reused == 120 && SampleQueue.runningText(pr).equals("Resuming shader check · translating 150 of 300"), "progress with reused entries");
        check(p.reused == 0, "no reused field: 0");
        check(SampleQueue.waitingText(0, true).equals("Waiting to resume shader check (next)") && SampleQueue.waitingText(2, false).equals("Waiting to check shaders (2 ahead)"), "waiting words");
        check(SampleQueue.backoffText(0).isEmpty() && SampleQueue.backoffText(1).equals("Resumes in about 1 min") && SampleQueue.backoffText(SampleQueue.BACKOFF_MS).equals("Resumes in about 10 min"), "backoff words");

        // backoff after an interruption
        long now = 1_000_000_000_000L, B = SampleQueue.BACKOFF_MS;
        check(SampleQueue.backoffLeft(0, now) == 0, "no history: no wait (the first launch queues at once)");
        check(SampleQueue.backoffLeft(now - 1000, now) == B - 1000 && SampleQueue.backoffLeft(now - B, now) == 0, "10 min after the interruption");
        check(SampleQueue.backoffLeft(now + 2 * B, now) == 0, "a time far ahead of the clock holds nothing");

        // the skip record: counts only, this APK, 7 days
        String rec = SampleQueue.skipText(SampleQueue.SKIPPED, now, "0.3.40-abc123", 40, 300);
        check(rec.contains("\"why\": \"skip\"") && rec.contains("\"done\": 40") && !rec.matches("(?s).*[0-9a-f]{16}.*"), "record: why and counts, no key");
        check(SampleQueue.skipHolds(rec, "0.3.40-abc123", now + 1000), "holds for this APK");
        check(!SampleQueue.skipHolds(rec, "0.3.28-def456", now + 1000), "another APK asks again");
        check(!SampleQueue.skipHolds(rec, "0.3.40-abc123", now + SampleQueue.SKIP_MS), "7 days later it asks again");
        check(!SampleQueue.skipHolds(rec, "0.3.40-abc123", now - 2 * 24 * 3600_000L) && !SampleQueue.skipHolds(null, "x", now) && !SampleQueue.skipHolds("{}", "x", now), "bad or future records hold nothing");

        // on disk: the record and the work folder's times
        try {
            java.io.File pack = java.nio.file.Files.createTempDirectory("samplequeue").toFile(), sh = new java.io.File(pack, "shaders"), work = new java.io.File(sh, ".sample-work");
            check(work.mkdirs(), "work folder");
            long t = System.currentTimeMillis();
            check(!SampleQueue.skipped(pack, "aaaaaaaaaaaa", "apk", t), "no record");
            SampleQueue.writeSkip(pack, "aaaaaaaaaaaa", SampleQueue.FAILED, t, "apk", 0, 0);
            check(SampleQueue.skipFile(pack, "aaaaaaaaaaaa").getName().equals(".sample-skip-aaaaaaaaaaaa.json") && SampleQueue.skipped(pack, "aaaaaaaaaaaa", "apk", t), "written and read back");
            check(!SampleQueue.skipped(pack, "bbbbbbbbbbbb", "apk", t), "another version of the tools asks again");
            check(SampleQueue.interruptedAt(work) == 0, "no resume.json: no history");
            java.nio.file.Files.write(new java.io.File(work, SampleQueue.RESUME).toPath(), "{}".getBytes());
            check(new java.io.File(work, SampleQueue.RESUME).setLastModified(t - 3_600_000L), "old key");
            check(Math.abs(SampleQueue.interruptedAt(work) - (t - 3_600_000L)) < 2000, "a killed run: its newest file's time");
            java.nio.file.Files.write(new java.io.File(work, SampleQueue.STOPPED).toPath(), ("{\"at_ms\": " + (t + 5000) + ", \"done\": 3, \"total\": 9}").getBytes());
            check(SampleQueue.interruptedAt(work) == t + 5000, "a stop: its recorded time");
            for (java.io.File f : work.listFiles()) f.delete();
            for (java.io.File f : sh.listFiles()) f.delete();
            sh.delete(); pack.delete();
        } catch (java.io.IOException e) { throw new AssertionError(e); }
        System.out.println("ok");
    }
}
