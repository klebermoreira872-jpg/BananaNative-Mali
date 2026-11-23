package dev.nxnative.android;

/** A game's own name (GameNames) on the JVM; prints "ok &lt;n&gt;" and exits 0, or the first failure and exits 1. Run by dm/tools/tests/test_android_gamenames.py */
public final class GameNamesJvmTest {
    private static int n;

    private static void eq(Object want, Object got, String what) {
        n++;
        if (!want.equals(got)) { System.out.println("FAIL " + what + ": want " + want + ", got " + got); System.exit(1); }
    }

    public static void main(String[] a) {
        eq("Zelda", GameNames.clean("  Zelda \n"), "trim");
        eq("A B", GameNames.clean("A\t\tB"), "tabs and runs of blanks become one space");
        eq("", GameNames.clean("   "), "blank is empty");
        eq("", GameNames.clean(null), "null is empty");
        eq(GameNames.MAX, GameNames.clean("x".repeat(200)).length(), "at most MAX");

        String id = GameOrder.id("0400486024DEC000", "/p/oot");
        String d = GameNames.put("", id, "The Legend of Zelda: Ocarina of Time", "OoT");
        eq(true, GameNames.renamed(d, id, "OoT"), "renamed when the entry has the player's name");
        eq(false, GameNames.renamed(d, id, "The Legend of Zelda: Ocarina of Time"), "not renamed with the game's own name");
        eq("The Legend of Zelda: Ocarina of Time", GameNames.original(d, id, "OoT"), "original from the player's name");
        eq("Other", GameNames.original(d, id, "Other"), "a name that is neither stays");
        eq("OoT", GameNames.apply(d, id, "The Legend of Zelda: Ocarina of Time"), "a new scan with the game's own name keeps the player's name");
        eq("OoT", GameNames.apply(d, id, "OoT"), "the player's name stays");
        eq("Renamed by the game", GameNames.apply(d, id, "Renamed by the game"), "a changed own name is not overwritten");
        eq("X", GameNames.apply(d, GameOrder.id("0400486024DEC000", "/p/other"), "X"), "another pack is another game");

        String d2 = GameNames.put(d, GameOrder.id("0100000000AA0000", "/p/a"), "A", "B");
        eq(2, GameNames.parse(d2).size(), "two games");
        eq(1, GameNames.parse(GameNames.remove(d2, id)).size(), "remove one");
        eq("A", GameNames.apply(GameNames.remove(d, id), id, "A"), "after remove nothing changes");
        eq(0, GameNames.parse("junk\nonly\ttwo\n\t\t\n").size(), "damaged lines are skipped");
        System.out.println("ok " + n);
    }
}
