package dev.nxnative.android;

import java.io.File;

/**
 * The launcher's shader states on the JVM (ShaderState, ShaderLibs.layerWritable, ShaderLibs.importProblem), driven by dm/tools/tests/test_android_shader_state.py. Commands, one per run:
 * <pre>
 * off &lt;title ID&gt; &lt;switch 0|1&gt; &lt;env|-&gt; &lt;writable 0|1&gt;                 → "off &lt;NONE|NOT_SWITCH2|SWITCH|ENV|UNWRITABLE&gt;" (ShaderState.layerOff)
 * needed &lt;off&gt; &lt;other inputs 0|1&gt; &lt;dump 0|1&gt; &lt;delta&gt; &lt;total&gt;          → the "Shaders needed" text (ShaderState.neededText; minutes "about 9-40 minutes")
 * ondemand &lt;dump 0|1&gt;                                                → the on-demand row's text, then a tab and the note (ShaderState.onDemandText, onDemandNote)
 * writable &lt;pack&gt; &lt;temp|-&gt;                                          → "writable true|false" (ShaderLibs.layerWritable)
 * import &lt;lib&gt; &lt;title ID&gt; &lt;current&gt; &lt;abi&gt; &lt;compat|-&gt; &lt;inputs|-&gt;     → "import ok v-&lt;V&gt;" or "import &lt;why not&gt;" (ShaderLibs.importProblem)
 * legacy &lt;dump 0|1&gt;                                                  → ShaderLibs.legacyWarning
 * need &lt;covered&gt; &lt;older plays&gt; &lt;code&gt; &lt;shaders&gt; (0|1 each)            → "need &lt;ShaderState.Need&gt;" (ShaderState.need)
 * autodelta &lt;delta&gt; &lt;total&gt; &lt;plays meanwhile 0|1&gt;                       → "autodelta true|false" (ShaderLibs.autoDelta)
 * skip &lt;covered&gt; &lt;older library&gt; &lt;redoes code&gt; &lt;pack plays now&gt;      → "skip true|false" (ShaderState.canSkipShaders)
 * </pre>
 */
public final class ShaderStateJvmTest {
    public static void main(String[] a) {
        switch (a[0]) {
            case "off":
                System.out.println("off " + ShaderState.layerOff(a[1], a[2].equals("1"), a[3].equals("-") ? null : a[3].replace("\\n", "\n"), a[4].equals("1")));
                break;
            case "needed":
                System.out.println(ShaderState.neededText(ShaderState.Off.valueOf(a[1]), a[2].equals("1"), a[3].equals("1"), Integer.parseInt(a[4]), Integer.parseInt(a[5]), "about 9-40 minutes"));
                break;
            case "ondemand":
                System.out.println(ShaderState.onDemandText(a[1].equals("1")) + "\t" + ShaderState.onDemandNote(a[1].equals("1")));
                break;
            case "writable":
                System.out.println("writable " + ShaderLibs.layerWritable(new File(a[1]), a[2].equals("-") ? null : new File(a[2])));
                break;
            case "import": {
                File f = new File(a[1]);
                ShaderLibs.Header h = ShaderLibs.header(f);
                String why = ShaderLibs.importProblem(h, f.length(), a[2], a[3], a[4], a[5].equals("-") ? null : a[5], a[6].equals("-") ? null : a[6]);
                System.out.println("import " + (why == null ? "ok v-" + h.vkChain : why));
                break;
            }
            case "legacy":
                System.out.println(ShaderLibs.legacyWarning(a[1].equals("1")));
                break;
            case "need":
                System.out.println("need " + ShaderState.need(a[1].equals("1"), a[2].equals("1"), a[3].equals("1"), a[4].equals("1")));
                break;
            case "autodelta":
                System.out.println("autodelta " + ShaderLibs.autoDelta(Integer.parseInt(a[1]), Integer.parseInt(a[2]), a[3].equals("1")));
                break;
            case "skip":
                System.out.println("skip " + ShaderState.canSkipShaders(a[1].equals("1"), a[2].equals("1"), a[3].equals("1"), a[4].equals("1")));
                break;
            default:
                throw new IllegalArgumentException(a[0]);
        }
    }
}
