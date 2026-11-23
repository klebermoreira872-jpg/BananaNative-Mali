package dev.nxnative.android;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** TouchHidden (the on-screen controls the player hid) on the JVM: parsing, the round trip, toggling, the last visible control, an unknown key. Prints "ok" or throws */
public final class TouchHiddenJvmTest {
    private static void check(boolean c, String what) { if (!c) throw new AssertionError(what); }

    public static void main(String[] args) {
        List<String> all = Arrays.asList("zl", "l", "zr", "r", "l3", "r3");
        check(TouchHidden.parse(null, all).isEmpty() && TouchHidden.parse("", all).isEmpty(), "nothing stored: nothing hidden (an existing layout is unchanged)");
        Set<String> h = TouchHidden.parse("l3, r3,bogus,,zl", all);
        check(h.equals(new LinkedHashSet<>(Arrays.asList("l3", "r3", "zl"))), "unknown keys and blanks dropped: " + h);
        check(TouchHidden.encode(h).equals("l3,r3,zl") && TouchHidden.parse(TouchHidden.encode(h), all).equals(h), "round trip");
        Set<String> t = TouchHidden.toggle(Collections.<String>emptySet(), "l3", all);
        check(t.equals(Collections.singleton("l3")), "hide one");
        check(TouchHidden.toggle(t, "l3", all).isEmpty(), "show it again");
        Set<String> most = new LinkedHashSet<>(Arrays.asList("zl", "l", "zr", "r", "l3"));
        check(TouchHidden.toggle(most, "r3", all).equals(most), "the last visible control stays");
        check(TouchHidden.toggle(most, "l3", all).size() == 4, "showing one of many");
        check(TouchHidden.toggle(Collections.<String>emptySet(), "nope", all).isEmpty(), "an unknown key changes nothing");
        System.out.println("ok");
    }
}
