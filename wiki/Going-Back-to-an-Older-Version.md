# Going back to an older version

If a new version plays worse for you than an older one, read this first. Going back is possible, but Android makes you uninstall the app, and that deletes the app's storage.

## Usually: wait for the fix

- If you want fewer changes, use the **Stable** channel: Settings > **Updates** > **Update channel** ([Updates](Updates#update-channels-stable-and-hotfix)). Stable skips the small fixes between the weekly releases.
- A release that breaks something is fixed by a new release, a **critical** update, which can also bring the earlier behaviour back. The app offers it like any update, so usually the easiest way back is to wait for it.
- **Tell us.** Open an issue that names the last version that worked for you and what got worse (game, phone, GPU driver). That is how a bad change gets found and undone for everyone.

## What uninstalling deletes

Android will not install an older version over a newer one, so going back means uninstalling first. Uninstalling deletes the app's storage, `Android/data/<app>/files`: your saves, your prepared games (packs), games copied into the app, and your settings ([What uninstalling deletes](Saves-and-Storage#what-uninstalling-deletes)). Your dumps and `.nup` files stay, and so do save backups in `save-backups/<title ID>/` next to your games.

## Steps

1. **Make sure your saves are backed up.** With **Back up saves before updating** on (Settings > **Updates**, on by default) and **All files access** allowed, the app backs up every changed save before each in-app update. You can also do it yourself: the game's ... button > **Back up saves**. Backups go to `save-backups/<title ID>/` next to the game folder, for example `Switch2/save-backups/040074A01BF12000/`, outside the app's storage. A game copied into the app, or used without All files access, gets a `.zip` you save somewhere instead: keep that file. See [Saves and storage](Saves-and-Storage#back-up-restore-import).
2. **Uninstall** the app.
3. **Install the older APK** from the project's [releases page](https://git.eden-emu.dev/moceure/BananaNative/releases). Download only from there.
4. **Add your games again** and **restore your saves:** the game's ... button > **Restore saves**, and pick the newest backup (or **Import save** for a `.zip`).
5. **Prepare** each game again. This takes a while, as on the first start ([First start and Prepare](First-Start-and-Prepare)).

The older version offers the newer release at start: choose **Later** to stay on it.
