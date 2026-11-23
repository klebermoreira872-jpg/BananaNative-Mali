package dev.nxnative.android;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Mods (the data mods' folders and zip import) on the JVM, driven by dm/tools/tests/test_android_mods.py. Prints "ok" or the failed checks. */
public final class ModsJvmTest {
    private static int fails;
    private static void check(boolean c, String m) { if (!c) { fails++; System.out.println("FAIL " + m); } }

    private static byte[] zip(String... entries) throws IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        try (ZipOutputStream z = new ZipOutputStream(b)) {
            for (String e : entries) { z.putNextEntry(new ZipEntry(e)); if (!e.endsWith("/")) z.write(e.getBytes(StandardCharsets.UTF_8)); z.closeEntry(); }
        }
        return b.toByteArray();
    }

    public static void main(String[] args) throws Exception {
        File tmp = Files.createTempDirectory("mods").toFile();
        File root = Mods.root(tmp, "0400A3A01EE4C000");
        check(root.getPath().endsWith("mods/0400A3A01EE4C000"), "root path");
        check(Mods.list(root).isEmpty(), "no mods yet");

        check(Mods.safeName("My Mod v1.zip").equals("My Mod v1"), "name keeps spaces, drops .zip");
        check(Mods.safeName("a:b/../c.zip").equals("c"), "name drops the path");
        check(Mods.safeName("x:y.zip").equals("x_y"), "name replaces the list separator");
        check(Mods.safeName("...").equals("mod") && Mods.safeName(null).equals("mod") && Mods.safeName(".hidden.zip").equals("hidden"), "name never empty or hidden");

        // a flat zip is taken as it is; a wrapper folder named like the zip is dropped
        Mods.Imported a = Mods.importZip(new ByteArrayInputStream(zip("motor_asset_re/a.bin", "motor_asset_re/b/c.bin")), root, "Flat.zip");
        check(a.dir.getName().equals("Flat") && a.files == 2 && new File(a.dir, "motor_asset_re/a.bin").isFile(), "flat zip kept whole");
        Mods.Imported w = Mods.importZip(new ByteArrayInputStream(zip("Wrapped/", "Wrapped/x.bin", "Wrapped/y/z.bin")), root, "Wrapped.zip");
        check(new File(w.dir, "x.bin").isFile() && new File(w.dir, "y/z.bin").isFile() && !new File(w.dir, "Wrapped").exists(), "wrapper named like the zip dropped");
        Mods.Imported v = Mods.importZip(new ByteArrayInputStream(zip("2.0.1/romfs/p.bin", "2.0.1/romfs/q.bin")), root, "Vers.zip");
        check(new File(v.dir, "p.bin").isFile() && v.files == 2, "version and romfs wrappers dropped");
        Mods.Imported s = Mods.importZip(new ByteArrayInputStream(zip("data/only.bin")), root, "Single.zip");
        check(new File(s.dir, "data/only.bin").isFile(), "a single folder that is not a wrapper stays (the game's own folder)");
        Mods.Imported mac = Mods.importZip(new ByteArrayInputStream(zip("__MACOSX/._a", "m.bin", "dir/.DS_Store", "dir/n.bin")), root, "Mac.zip");
        check(mac.files == 2 && !new File(mac.dir, "__MACOSX").exists(), "macOS metadata skipped: " + mac.files);

        // the same name again gets a number
        Mods.Imported again = Mods.importZip(new ByteArrayInputStream(zip("k.bin")), root, "Flat.zip");
        check(again.dir.getName().equals("Flat 2"), "name taken: " + again.dir.getName());
        check(Mods.names(root).equals(Arrays.asList("Flat", "Flat 2", "Mac", "Single", "Vers", "Wrapped")), "list by name: " + Mods.names(root));
        check(new File(root.getPath()).list((d, n) -> n.startsWith(".")).length == 0, "no temporary folder left");

        // paths that leave the mod are refused and leave nothing behind
        for (String bad : new String[] {"../evil.bin", "a/../../evil.bin", "/abs.bin", "C:/win.bin", "a\\..\\..\\evil.bin"}) {
            int before = Mods.list(root).size();
            boolean refused = false;
            try { Mods.importZip(new ByteArrayInputStream(zip(bad)), root, "Bad.zip"); } catch (IOException e) { refused = true; }
            check(refused && Mods.list(root).size() == before, "refused: " + bad);
        }
        check(!new File(root, "evil.bin").exists() && !new File(tmp, "evil.bin").exists() && !new File(tmp, "mods/evil.bin").exists(), "nothing written outside");
        boolean empty = false;
        try { Mods.importZip(new ByteArrayInputStream(zip("only/")), root, "Empty.zip"); } catch (IOException e) { empty = true; }
        check(empty, "a zip with no files is refused");

        // the overlay: the mods that are on, in order, as a ':' list; added after the Resolution choice's
        Set<String> off = new TreeSet<>(Collections.singleton("Flat 2"));
        String ov = Mods.overlay(root, off);
        check(!ov.contains("Flat 2") && ov.startsWith(new File(root, "Flat").getPath() + ":" + new File(root, "Mac").getPath()), "overlay: " + ov);
        check(Mods.on(root, off) == 5 && Mods.on(root, new TreeSet<>()) == 6, "count on");
        List<String> env = new ArrayList<>(Arrays.asList("A=1", "DM_ROMFS_OVERLAY=/pack/scene_res/720p", "B=2"));
        Mods.addTo(env, ov);
        check(env.get(1).equals("DM_ROMFS_OVERLAY=/pack/scene_res/720p:" + ov) && env.size() == 3, "appended to the scene overlay");
        List<String> env2 = new ArrayList<>(Collections.singletonList("A=1"));
        Mods.addTo(env2, ov);
        check(env2.equals(Arrays.asList("A=1", "DM_ROMFS_OVERLAY=" + ov)), "own line");
        List<String> env3 = new ArrayList<>(Collections.singletonList("A=1"));
        Mods.addTo(env3, "");
        check(env3.size() == 1, "nothing to add");

        // off list round trip
        check(Mods.decodeOff(Mods.encodeOff(off)).equals(off) && Mods.decodeOff("").isEmpty() && Mods.decodeOff(null).isEmpty(), "off list");

        check(Mods.countFiles(w.dir) == 2, "countFiles");
        Mods.remove(root, "Wrapped");
        Mods.remove(root, "../Flat");
        Mods.remove(root, ".");
        check(!new File(root, "Wrapped").exists() && new File(root, "Flat").isDirectory(), "remove one mod only");

        Mods.deleteTree(tmp);
        System.out.println(fails == 0 ? "ok" : fails + " failures");
        System.exit(fails == 0 ? 0 : 1);
    }
}
