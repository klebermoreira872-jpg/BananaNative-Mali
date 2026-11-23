package dev.nxnative.android;

/**
 * SkipNotice on the JVM, driven by dm/tools/tests/test_android_skipnotice.py. Commands, one per run:
 * <pre>
 * percent &lt;status or -&gt;           → "percent &lt;n&gt;"
 * causes &lt;status or -&gt;            → "causes &lt;text&gt;"
 * text &lt;percent&gt;    → "text &lt;the notice&gt;"
 * driver &lt;DM_VK_DRIVER line or -&gt; &lt;installed folder or -&gt;    → "driver &lt;name&gt;"
 * nomesh &lt;status&gt; &lt;percent&gt;       → "nomesh &lt;true|false&gt; &lt;the notice&gt;"
 * missing &lt;status&gt; &lt;percent&gt;      → "missing &lt;true|false&gt; &lt;the notice&gt;"
 * </pre>
 */
public final class SkipNoticeJvmTest {
    public static void main(String[] a) {
        String s = a.length > 1 && !a[1].equals("-") ? a[1] : null;
        switch (a[0]) {
            case "percent": System.out.println("percent " + SkipNotice.percent(s)); break;
            case "causes": System.out.println("causes " + SkipNotice.causes(s)); break;
            case "nomesh": System.out.println("nomesh " + SkipNotice.noMesh(s) + " " + SkipNotice.textNoMesh(Integer.parseInt(a[2]))); break;
            case "missing": System.out.println("missing " + SkipNotice.missingShaders(s) + " " + SkipNotice.textMissingShaders(Integer.parseInt(a[2]))); break;
            case "text": System.out.println("text " + SkipNotice.text(Integer.parseInt(a[1]))); break;
            case "driver": System.out.println("driver " + SkipNotice.driverName(a[1].equals("-") ? null : a[1], d -> d.equals(a[2]) ? "Mesa Turnip (27.0)" : null)); break;
            default: throw new IllegalArgumentException(a[0]);
        }
    }
}
