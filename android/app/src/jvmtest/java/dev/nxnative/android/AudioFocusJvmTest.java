package dev.nxnative.android;

/** AudioFocus on the JVM (dm/tools/tests/test_android_audiofocus.py): which focus changes interrupt the sound (on screen and in the background), and when the return asks for the focus again. Prints "ok" or throws */
public final class AudioFocusJvmTest {
    private static void check(boolean c, String what) { if (!c) throw new AssertionError(what); }

    public static void main(String[] args) {
        AudioFocus f = new AudioFocus();
        f.requested(true);
        check(!f.askAgain(), "granted at start: nothing to ask");
        // A call: transient, Android gives the focus back itself
        check(f.changed(AudioFocus.LOSS_TRANSIENT, true), "transient loss interrupts");
        check(!f.askAgain(), "transient loss: Android gives it back, no new request");
        check(!f.changed(AudioFocus.GAIN, true), "gain ends the interruption");
        check(f.changed(AudioFocus.LOSS_TRANSIENT_CAN_DUCK, true) && !f.askAgain(), "ducking: interrupted, given back by Android");
        check(!f.changed(AudioFocus.GAIN, true), "gain after ducking");
        // Another app plays music while the game is minimized: lost for good, asked again on the return
        check(f.changed(AudioFocus.LOSS, false), "permanent loss in the background interrupts");
        check(f.askAgain(), "permanent loss: ask again on the return");
        f.requested(false);
        check(f.askAgain(), "refused: ask again on the next return");
        f.requested(true);
        check(!f.askAgain(), "granted again: nothing more to ask");
        // A transient loss after a permanent one (the other app's prompt) does not forget that the request was dropped
        f.changed(AudioFocus.LOSS, false); f.changed(AudioFocus.LOSS_TRANSIENT, false);
        check(f.askAgain(), "still dropped");
        check(!f.changed(AudioFocus.GAIN, true) && !f.askAgain(), "a gain means it is held");
        // Refused at start: the first return asks
        AudioFocus g = new AudioFocus(); g.requested(false);
        check(g.askAgain(), "refused at start");
        check(!g.changed(0, true) && !g.changed(0, false), "an unknown change does not interrupt");
        // Another app plays while the game stays on screen (a second screen, split screen, a floating window): no return will ask again, so the sound goes on
        AudioFocus s = new AudioFocus(); s.requested(true);
        check(!s.changed(AudioFocus.LOSS, true), "permanent loss on screen does not interrupt");
        check(s.askAgain(), "permanent loss on screen: still asked again on the next return");
        check(!s.changed(AudioFocus.LOSS, true), "a second permanent loss on screen");
        check(s.changed(AudioFocus.LOSS_TRANSIENT, true) && !s.changed(AudioFocus.LOSS, true), "a permanent loss after a transient one ends the interruption while on screen");
        s.requested(true);
        check(!s.askAgain(), "granted on the return");
        // A call still interrupts on screen and in the background alike, and its end is Android's gain
        check(s.changed(AudioFocus.LOSS_TRANSIENT, true) && s.changed(AudioFocus.LOSS_TRANSIENT, false), "transient loss interrupts wherever the game is");
        check(s.changed(AudioFocus.LOSS_TRANSIENT_CAN_DUCK, false), "ducking in the background interrupts");
        check(!s.changed(AudioFocus.GAIN, false) && !s.askAgain(), "gain in the background");
        System.out.println("ok");
    }
}
