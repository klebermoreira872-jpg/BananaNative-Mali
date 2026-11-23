package dev.nxnative.android;

import java.io.File;

/**
 * LayerPending, LayerDir, LayerGuard and LayerStatus on the JVM (label &lt;n&gt; &lt;reason|-&gt; &lt;started&gt; and line &lt;on&gt; &lt;library&gt; &lt;built&gt; &lt;pending&gt; &lt;reason|-&gt; &lt;gaveUp&gt; → the label and the panel's line), driven by dm/tools/tests/test_android_layer.py. Commands: <pre>pending &lt;layer folder&gt; [version] → "pending &lt;n&gt; &lt;keys&gt;";
 * built &lt;layer&gt; [version] → "built &lt;n&gt;"; settled &lt;layer&gt; &lt;version&gt; → "settled &lt;n&gt;"; building &lt;layer&gt; &lt;now ms&gt; → "building true|false"; text &lt;n&gt; → "text &lt;indicator&gt;";
 * resolve &lt;pack&gt; &lt;temp&gt; → "resolve &lt;layer folder&gt; in-pack|temp" (LayerDir.resolve); tidy &lt;layer&gt; &lt;current&gt; [usable now-ms] → "tidy &lt;what was done&gt;" (LayerDir.tidy);
 * drop &lt;layer&gt; &lt;library&gt; &lt;title ID&gt; → "drop &lt;n&gt;" (LayerGuard.dropCovered); quota &lt;used&gt; &lt;usable&gt; &lt;library bytes&gt; → "quota &lt;bytes&gt;"; usage &lt;folder&gt; [version] → "usage &lt;bytes&gt;";
 * full &lt;layer&gt; &lt;version&gt; &lt;usable&gt; → "full &lt;used&gt; &lt;quota&gt;" or "full -" (LayerGuard.full; notefull &lt;layer&gt; &lt;used&gt; &lt;quota&gt; writes the note); storage &lt;used&gt; &lt;quota&gt; &lt;library&gt; &lt;dump&gt; → the page's words;
 * structure &lt;library&gt; → "structure ok|&lt;problem&gt;" (ShaderLibs.structureProblem); host &lt;pack&gt; &lt;title ID&gt; &lt;current&gt; &lt;abi&gt; → "host &lt;library path&gt;|-" (ShaderLibs.hostLibrary);
 * lock → "lock ok" (PackLock's rules, checked in place); pause &lt;thermal&gt; &lt;battery&gt; &lt;charging&gt; → "pause &lt;label or -&gt;"; pace &lt;thermal&gt; &lt;headroom&gt; &lt;battery&gt; &lt;charging&gt; &lt;pending&gt; &lt;uptime ms&gt; → "pace &lt;label or -&gt; | &lt;note&gt;"; label2 &lt;n&gt; &lt;reason|-&gt; &lt;started&gt; &lt;busy&gt; &lt;retry s&gt; &lt;note|-&gt;; building-own / clear-stale &lt;layer&gt; &lt;now ms&gt; &lt;package&gt; &lt;alive|dead&gt; (marker "pid\tpackage"); procs &lt;cores&gt; &lt;thermal&gt; → "procs &lt;n&gt;"</pre>
 */
public final class LayerPendingJvmTest {
    public static void main(String[] a) {
        switch (a[0]) {
            case "pending": { java.util.Set<String> p = a.length > 2 ? LayerPending.pending(new File(a[1]), a[2]) : LayerPending.pending(new File(a[1])); System.out.println("pending " + p.size() + " " + String.join(",", p)); break; }
            case "built": System.out.println("built " + LayerPending.built(new File(a[1]), a.length > 2 ? a[2] : null)); break;
            case "settled": System.out.println("settled " + LayerPending.settled(new File(a[1]), a[2])); break;
            case "building": System.out.println("building " + LayerPending.building(new File(a[1]), Long.parseLong(a[2]))); break;
            case "timing": { String t = LayerPending.lastTiming(new File(a[1])); System.out.println("timing " + (t == null ? "-" : t)); break; }
            case "text": System.out.println("text " + LayerPending.text(Integer.parseInt(a[1]))); break;
            case "resolve": { File l = LayerDir.resolve(new File(a[1]), new File(a[2])); System.out.println("resolve " + l.getPath() + " " + (LayerDir.inPack(l, new File(a[2])) ? "in-pack" : "temp")); break; }
            case "tidy": System.out.println("tidy " + (a.length > 4 ? LayerDir.tidy(new File(a[1]), a[2], Long.parseLong(a[4]), Long.parseLong(a[3])) : LayerDir.tidy(new File(a[1]), a[2]))); break;
            case "drop": System.out.println("drop " + LayerGuard.dropCovered(new File(a[1]), new File(a[2]), a[3])); break;
            case "quota": System.out.println("quota " + LayerGuard.quota(Long.parseLong(a[1]), Long.parseLong(a[2]), Long.parseLong(a[3]))); break;
            case "usage": System.out.println("usage " + (a.length > 2 ? LayerGuard.usage(new File(a[1]), a[2]) : LayerGuard.usage(new File(a[1])))); break;
            case "notefull": LayerGuard.noteFull(new File(a[1]), Long.parseLong(a[2]), Long.parseLong(a[3])); System.out.println("notefull done"); break;
            case "full": { long[] f = LayerGuard.full(new File(a[1]), a[2], Long.parseLong(a[3])); System.out.println("full " + (f == null ? "-" : f[0] + " " + f[1])); break; }
            case "storage": System.out.println("storage " + LayerStatus.storageText(Long.parseLong(a[1]), Long.parseLong(a[2]), Boolean.parseBoolean(a[3]), Boolean.parseBoolean(a[4]))); break;
            case "structure": { String p = ShaderLibs.structureProblem(new File(a[1])); System.out.println("structure " + (p == null ? "ok" : p)); break; }
            case "host": { File h = ShaderLibs.hostLibrary(new File(a[1]), a[2], a[3], a[4], null); System.out.println("host " + (h == null ? "-" : h.getPath())); break; }
            case "verifyonly": {   // verifyonly <layer> <library> <title ID> [version]: the requests that only verify a kept library (LayerKept.verifyOnly)
                try (LayerKept k = new LayerKept(new File(a[2]), a[3])) {
                    File layer = new File(a[1]);
                    java.util.Set<String> v = new java.util.TreeSet<>(k.verifyOnly(new File(layer, "req"), LayerPending.requested(layer), LayerPending.builtKeys(layer, a.length > 4 ? a[4] : null)));
                    System.out.println("verifyonly " + k.ok() + " " + String.join(",", v));
                }
                break;
            }
            case "kept": System.out.println("kept " + ShaderLibs.kept(new File(a[1]))); break;
            case "lock": lock(); System.out.println("lock ok"); break;
            case "pause": { String r = LayerGuard.pauseReason(Integer.parseInt(a[1]), Integer.parseInt(a[2]), Boolean.parseBoolean(a[3])); System.out.println("pause " + (r == null ? "-" : LayerGuard.pausedText(r))); break; }
            case "label": { String l = LayerStatus.label(Integer.parseInt(a[1]), a[2].equals("-") ? null : a[2], Boolean.parseBoolean(a[3])); System.out.println("label " + (l == null ? "-" : l)); break; }
            case "line": System.out.println("line " + LayerStatus.panelLine(Boolean.parseBoolean(a[1]), Boolean.parseBoolean(a[2]), Integer.parseInt(a[3]), Integer.parseInt(a[4]), a[5].equals("-") ? null : a[5], Boolean.parseBoolean(a[6]))); break;
            case "pace": { LayerGuard.Pace r = LayerGuard.pace(Integer.parseInt(a[1]), Float.parseFloat(a[2]), Integer.parseInt(a[3]), Boolean.parseBoolean(a[4]), Integer.parseInt(a[5]), Long.parseLong(a[6])); System.out.println("pace " + (r.pause == null ? "-" : LayerGuard.pausedText(r.pause)) + " | " + r.note); break; }
            case "shown": { String l = LayerStatus.shown(Integer.parseInt(a[1]), Integer.parseInt(a[2]), a[3].equals("-") ? null : a[3], Boolean.parseBoolean(a[4]), Boolean.parseBoolean(a[5]), 0, a[6].equals("-") ? null : a[6]); System.out.println("shown " + (l == null ? "-" : l)); break; }
            case "due": System.out.println("due " + LayerStatus.buildDue(Integer.parseInt(a[1]), Boolean.parseBoolean(a[2]), Boolean.parseBoolean(a[3]), a[4].equals("-") ? null : a[4], Boolean.parseBoolean(a[5]), Long.parseLong(a[6]), Long.parseLong(a[7]), Long.parseLong(a[8]))); break;
            case "label2": System.out.println("label2 " + LayerStatus.label(Integer.parseInt(a[1]), a[2].equals("-") ? null : a[2], Boolean.parseBoolean(a[3]), Boolean.parseBoolean(a[4]), Integer.parseInt(a[5]), a[6].equals("-") ? null : a[6])); break;
            case "building-own": { LayerPending.selfPackage = a[3]; LayerPending.alive = pid -> a[4].equals("alive"); System.out.println("building-own " + LayerPending.building(new File(a[1]), Long.parseLong(a[2]))); break; }
            case "clear-stale": { LayerPending.selfPackage = a[3]; LayerPending.alive = pid -> a[4].equals("alive"); System.out.println("clear-stale " + LayerPending.clearStale(new File(a[1]), Long.parseLong(a[2]))); break; }
            case "procs": System.out.println("procs " + LayerGuard.procs(Integer.parseInt(a[1]), Integer.parseInt(a[2]), Integer.parseInt(a[3]), a.length > 4 ? Float.parseFloat(a[4]) : Float.NaN)); break;
            default: throw new IllegalArgumentException(a[0]);
        }
    }

    private static void check(boolean ok, String what) { if (!ok) throw new AssertionError(what); }

    /** PackLock: a layer build and a Prepare job never hold the packer's Python at once */
    private static void lock() {
        check(PackLock.tryLayer(), "a layer build starts when nothing runs");
        check(!PackLock.tryLayer(), "one layer build at a time");
        check(!PackLock.layerStopAsked(), "no job: the build goes on");
        check(PackLock.beginJob(), "a job that starts sees the build that runs");
        check(PackLock.layerStopAsked(), "the build is asked to stop");
        try { check(!PackLock.awaitLayerEnd(50), "the job waits while the build runs"); } catch (InterruptedException e) { throw new AssertionError(e); }
        Thread end = new Thread(() -> { try { Thread.sleep(100); } catch (InterruptedException e) { return; } PackLock.endLayer(); });
        end.start();
        try { check(PackLock.awaitLayerEnd(5000), "the job goes on once the build ended"); end.join(); } catch (InterruptedException e) { throw new AssertionError(e); }
        check(!PackLock.tryLayer(), "no layer build while a job exists (between its steps too)");
        check(!PackLock.beginJob(), "nothing to wait for");
        PackLock.endJob();
        check(!PackLock.tryLayer(), "a job still exists");
        PackLock.endJob();
        check(PackLock.tryLayer(), "a layer build starts once the jobs ended");
        PackLock.endLayer();
        check(!PackLock.layerRunning() && !PackLock.jobRunning(), "nothing holds it");
    }
}
