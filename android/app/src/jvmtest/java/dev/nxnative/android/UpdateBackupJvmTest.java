package dev.nxnative.android;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.TreeMap;

/**
 * UpdateBackup on the JVM (dm/tools/tests/test_android_updatebackup.py): the automatic save backup before an update. A changed save is backed up, an unchanged one
 * skipped, an empty one skipped, a backups folder in app storage or one the app may not write refused, a save in use skipped, and nothing is ever deleted or
 * overwritten. Prints "ok" or throws. args[0]: an empty work folder
 */
public final class UpdateBackupJvmTest {
    private static void check(boolean c, String what) { if (!c) throw new AssertionError(what); }

    private static void write(File f, String s) throws IOException {
        f.getParentFile().mkdirs();
        Files.write(f.toPath(), s.getBytes(StandardCharsets.UTF_8));
    }

    /** Everything under d: relative path → content ("/" for a folder) */
    private static TreeMap<String, String> tree(File d) throws IOException {
        TreeMap<String, String> m = new TreeMap<>();
        tree(d, "", m);
        return m;
    }

    private static void tree(File d, String rel, TreeMap<String, String> m) throws IOException {
        String[] l = d.list();
        if (l == null) return;
        Arrays.sort(l);
        for (String n : l) {
            File f = new File(d, n);
            String r = rel.isEmpty() ? n : rel + "/" + n;
            if (f.isDirectory()) { m.put(r, "/"); tree(f, r, m); }
            else m.put(r, new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8));
        }
    }

    /** The finished backups (folders with their manifest) in a backups folder */
    private static List<String> backups(File dir) {
        List<String> out = new ArrayList<>();
        for (SaveStore.Backup b : SaveStore.list(dir)) out.add(b.name);
        return out;
    }

    public static void main(String[] args) throws Exception {
        File root = new File(args[0]).getAbsoluteFile();
        File app = new File(root, "Android/data/dev.bananative.android/files"), shared = new File(root, "Switch2");
        app.mkdirs();
        shared.mkdirs();

        // A game with a save and a device save, on shared storage
        File save = new File(app, "saves/040074A01BF12000"), backupsDir = Prefs0.backupsDir(new File(shared, "dkb.nup"), "040074A01BF12000");
        write(new File(save, "save.dat"), "one");
        write(new File(SaveStore.device(save), "dev.dat"), "device");
        UpdateBackup.Item dkb = new UpdateBackup.Item("040074A01BF12000", "DKB", "", save, save, backupsDir, true);

        // A second user's save of the same game
        File user = new File(save.getParentFile(), save.getName() + "_user_0123456789abcdef0123456789abcdef");
        write(new File(user, "u.dat"), "user");
        UpdateBackup.Item dkbUser = new UpdateBackup.Item("040074A01BF12000", "DKB", "01234567", user, save, backupsDir, true);

        // An empty save (a game never played: its folder only, with an empty sub-folder)
        File emptySave = new File(app, "saves/0100000000000001");
        new File(emptySave, "sub").mkdirs();
        UpdateBackup.Item empty = new UpdateBackup.Item("0100000000000001", "Empty", "", emptySave, emptySave, new File(shared, "save-backups/0100000000000001"), true);

        // A game copied into the app: its backups folder would be in app storage
        File copiedSave = new File(app, "saves/0100000000000002");
        write(new File(copiedSave, "c.dat"), "copied");
        UpdateBackup.Item copied = new UpdateBackup.Item("0100000000000002", "Copied", "", copiedSave, copiedSave, new File(app, "games/save-backups/0100000000000002"), true);

        // No All files access: the shared folder cannot be written
        File noAccessSave = new File(app, "saves/0100000000000003");
        write(new File(noAccessSave, "n.dat"), "n");
        UpdateBackup.Item noAccess = new UpdateBackup.Item("0100000000000003", "NoAccess", "", noAccessSave, noAccessSave, new File(shared, "save-backups/0100000000000003"), false);

        List<UpdateBackup.Item> all = Arrays.asList(dkb, dkbUser, empty, copied, noAccess);

        // Refusals: the in-app folder and the missing access; an empty save is never asked about
        check(UpdateBackup.empty(emptySave) && !UpdateBackup.empty(save), "empty: folders alone do not count");
        check(UpdateBackup.IN_APP.equals(UpdateBackup.refuse(copied, app)), "a backups folder in app storage is refused");
        check(UpdateBackup.NO_ACCESS.equals(UpdateBackup.refuse(noAccess, app)), "a backups folder the app may not write is refused");
        check(UpdateBackup.refuse(dkb, app) == null, "a shared backups folder is fine");
        List<UpdateBackup.Result> blocked = UpdateBackup.blocked(all, app);
        check(blocked.size() == 2 && blocked.get(0).item == copied && blocked.get(1).item == noAccess, "blocked: the copied game and the one without access");

        // First run: both DKB saves backed up (with the device save), the others skipped
        List<UpdateBackup.Result> r = UpdateBackup.run(all, app, "20261121-100000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.BACKED_UP && r.get(1).outcome == UpdateBackup.Outcome.BACKED_UP, "changed saves backed up: " + r.get(0).detail + " / " + r.get(1).detail);
        check(r.get(2).outcome == UpdateBackup.Outcome.EMPTY, "empty skipped");
        check(r.get(3).outcome == UpdateBackup.Outcome.REFUSED && UpdateBackup.IN_APP.equals(r.get(3).detail), "in-app refused");
        check(r.get(4).outcome == UpdateBackup.Outcome.REFUSED && UpdateBackup.NO_ACCESS.equals(r.get(4).detail), "no access refused");
        check(UpdateBackup.gamesBackedUp(r) == 1, "one game");
        check(backups(backupsDir).equals(Arrays.asList("20261121-100000-before-update-user-01234567", "20261121-100000-before-update")), "names: " + backups(backupsDir));
        File first = new File(backupsDir, "20261121-100000-before-update");
        check(new File(first, "main/save.dat").isFile() && new File(first, "device/dev.dat").isFile(), "the device save is in the backup");
        check(!new File(app, "games/save-backups").exists() && !new File(shared, "save-backups/0100000000000003").exists() && !new File(shared, "save-backups/0100000000000001").exists(),
                "nothing written for skipped saves");

        // Second run with nothing changed: no new backup
        TreeMap<String, String> before = tree(root);
        r = UpdateBackup.run(all, app, "20261121-110000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.UNCHANGED && r.get(1).outcome == UpdateBackup.Outcome.UNCHANGED, "unchanged saves skipped");
        check(UpdateBackup.gamesBackedUp(r) == 0, "no game backed up");
        TreeMap<String, String> after = tree(root);
        after.keySet().removeIf(k -> k.endsWith(".lock"));
        before.keySet().removeIf(k -> k.endsWith(".lock"));
        check(after.equals(before), "an unchanged run writes nothing");

        // A changed save (main or device) is backed up again; the older backup stays as it was
        TreeMap<String, String> old = tree(first);
        write(new File(SaveStore.device(save), "dev.dat"), "device 2");
        r = UpdateBackup.run(all, app, "20261121-120000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.BACKED_UP && r.get(1).outcome == UpdateBackup.Outcome.UNCHANGED, "only the changed save: " + r.get(0).outcome + " " + r.get(1).outcome);
        check(tree(first).equals(old), "the older backup is untouched");
        check(backups(backupsDir).size() == 3, "three backups: " + backups(backupsDir));

        // A manual backup (Manage › Back up saves) of the current save counts as its newest backup
        write(new File(save, "save.dat"), "two");
        SaveStore.backup(save, backupsDir, "20261121-130000");
        check(UpdateBackup.unchangedSince(save, backupsDir) != null, "a manual backup counts");

        // A damaged newest backup: a new one is made, the damaged one is left as it is
        write(new File(backupsDir, "20261121-130000/main/save.dat"), "broken");
        check(UpdateBackup.unchangedSince(save, backupsDir) == null, "a damaged newest backup does not count");
        r = UpdateBackup.run(Arrays.asList(dkb), app, "20261121-140000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.BACKED_UP, "backed up again after damage");
        check("broken".equals(new String(Files.readAllBytes(new File(backupsDir, "20261121-130000/main/save.dat").toPath()), StandardCharsets.UTF_8)), "the damaged backup is left");

        // Same stamp twice: a free name, never over an existing backup
        write(new File(save, "save.dat"), "three");
        r = UpdateBackup.run(Arrays.asList(dkb), app, "20261121-140000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.BACKED_UP && r.get(0).detail.endsWith("20261121-140000-before-update-2"), "a free name: " + r.get(0).detail);

        // In use (the game runs: the launcher's busy check, or the lock held): skipped, nothing written
        write(new File(save, "save.dat"), "four");
        int n = backups(backupsDir).size();
        r = UpdateBackup.run(Arrays.asList(dkb), app, "20261121-150000", it -> true, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.IN_USE, "busy skipped");
        try (SaveStore.Lock l = SaveStore.lock(save)) {
            r = UpdateBackup.run(Arrays.asList(dkb), app, "20261121-150000", null, null);
            check(r.get(0).outcome == UpdateBackup.Outcome.IN_USE, "locked skipped");
        }
        check(backups(backupsDir).size() == n, "no backup while in use");

        // A failure (the backups folder is a file) is reported, the save is left
        File badDir = new File(shared, "save-backups/bad");
        write(badDir, "a file");
        UpdateBackup.Item bad = new UpdateBackup.Item("0100000000000004", "Bad", "", save, save, badDir, true);
        r = UpdateBackup.run(Arrays.asList(bad), app, "20261121-160000", null, null);
        check(r.get(0).outcome == UpdateBackup.Outcome.FAILED && r.get(0).detail != null, "a failure is reported");
        check("four".equals(new String(Files.readAllBytes(new File(save, "save.dat").toPath()), StandardCharsets.UTF_8)), "the save is left as it was");

        // Nothing deleted: every save file is still there
        check(new File(user, "u.dat").isFile() && new File(copiedSave, "c.dat").isFile() && new File(noAccessSave, "n.dat").isFile() && new File(emptySave, "sub").isDirectory(), "saves kept");
        System.out.println("ok");
    }

    /** Prefs.backupsDir without Android (Prefs needs a Context): &lt;the game's folder&gt;/save-backups/&lt;id&gt; */
    private static final class Prefs0 {
        static File backupsDir(File game, String id) { return new File(game.getAbsoluteFile().getParentFile(), "save-backups/" + id); }
    }
}
