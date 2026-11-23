package dev.nxnative.android;

/** BuildKind on the JVM, driven by dm/tools/tests/test_android_buildkind.py: "kind <versionName> <releaseKind|->" prints the kind, "base <versionName>", "log <kind>" */
public final class BuildKindJvmTest {
    public static void main(String[] a) {
        switch (a[0]) {
            case "kind": System.out.println("kind " + BuildKind.of(a[1], a[2].equals("-") ? "" : a[2])); break;
            case "base": System.out.println("base " + BuildKind.base(a[1])); break;
            case "log": System.out.println("log " + BuildKind.logNote(a[1].equals("-") ? "" : a[1])); break;
            case "hotfix": System.out.println("hotfix " + BuildKind.isHotfix(a[1])); break;
            default: throw new IllegalArgumentException(a[0]);
        }
    }
}
