package dev.nxnative.android;

import java.util.Arrays;

/**
 * PanelRates on the JVM: the fastest refresh from the display's modes and Android's peak setting, the multipliers and target rates frame generation offers for it, and a
 * saved choice held to what is offered. Run by dm/tools/tests/test_android_panelrates.py. Prints "ok" or throws
 */
public final class PanelRatesJvmTest {
    private static void check(boolean c, String what) { if (!c) throw new AssertionError(what); }
    private static void eq(int[] got, int[] want, String what) { check(Arrays.equals(got, want), what + ": " + Arrays.toString(got) + ", not " + Arrays.toString(want)); }

    public static void main(String[] a) {
        float[] thor = {60.000004f, 120.00001f};   // the AYN Thor's main screen (dumpsys display)
        // The peak setting holds the screen: the Thor with its system setting at 60 Hz, then at 120 or unset
        check(PanelRates.maxHz(thor, 60f) == 60, "Thor at a 60 Hz setting");
        check(PanelRates.maxHz(thor, 120f) == 120 && PanelRates.maxHz(thor, 0f) == 120 && PanelRates.maxHz(thor, Float.POSITIVE_INFINITY) == 120, "Thor unheld");
        check(PanelRates.maxHz(thor, 240f) == 120, "a peak above the fastest mode");
        check(PanelRates.maxHz(null, 60f) == 0 && PanelRates.maxHz(new float[0], 0f) == 0, "no modes: not known");
        check(PanelRates.maxHz(new float[]{59.94f}, 0f) == 60, "rounded");

        // Multipliers: a 30 fps game needs 60 Hz for 2x, 90 for 3x, 120 for 4x; 2x always; all when not known
        eq(PanelRates.multipliers(60), new int[]{2}, "60 Hz");
        eq(PanelRates.multipliers(90), new int[]{2, 3}, "90 Hz");
        eq(PanelRates.multipliers(120), new int[]{2, 3, 4}, "120 Hz");
        eq(PanelRates.multipliers(144), new int[]{2, 3, 4}, "144 Hz");
        eq(PanelRates.multipliers(30), new int[]{2}, "30 Hz: 2x stays");
        eq(PanelRates.multipliers(0), new int[]{2, 3, 4}, "not known");

        // Targets: Fixed always; a rate at most the screen's that a mode shows evenly
        eq(PanelRates.targets(60, thor), new int[]{0, 60}, "Thor at 60 Hz");
        eq(PanelRates.targets(120, thor), new int[]{0, 60, 120}, "Thor at 120 Hz: no 90 (not even on 120)");
        eq(PanelRates.targets(90, new float[]{60f, 90f}), new int[]{0, 60, 90}, "a 60/90 Hz panel");
        eq(PanelRates.targets(144, new float[]{60f, 90f, 120f, 144f}), new int[]{0, 60, 90, 120}, "a 60/90/120/144 Hz panel");
        eq(PanelRates.targets(0, null), new int[]{0, 60, 90, 120}, "not known");

        // A saved choice the screen cannot show: the largest offered under it, else the smallest
        check(PanelRates.clamp(4, new int[]{2}) == 2 && PanelRates.clamp(3, new int[]{2, 3, 4}) == 3, "multipliers");
        check(PanelRates.clamp(90, new int[]{0, 60, 120}) == 60 && PanelRates.clamp(120, new int[]{0, 60}) == 60 && PanelRates.clamp(0, new int[]{0, 60}) == 0, "targets");
        check(PanelRates.clamp(1, new int[]{2, 3}) == 2, "under every offered value");
        System.out.println("ok");
    }
}
