package dev.nxnative.android;

/** CropMath: the crop of a cover picture under a fixed frame (plain main, no framework: the same style as the other JvmTests) */
public final class CropMathJvmTest {
    static int fails;

    static void check(boolean ok, String what) { if (!ok) { fails++; System.out.println("FAIL " + what); } }
    static boolean near(float a, float b) { return Math.abs(a - b) < 0.01f; }

    public static void main(String[] args) {
        // a wide picture under a square frame: zoom 1 shows the full height and a square of the width, centred
        CropMath m = new CropMath(2000, 1000);
        m.frame(300, 300);
        float[] r = m.rect();
        check(near(r[0], 500) && near(r[1], 0) && near(r[2], 1500) && near(r[3], 1000), "wide, zoom 1: centre square " + java.util.Arrays.toString(r));
        // pan right by 150 view px = 500 picture px: the frame moves left on the picture, held at the picture's edge
        m.pan(150, 0);
        r = m.rect();
        check(near(r[0], 0) && near(r[2], 1000), "pan stops at the left edge " + java.util.Arrays.toString(r));
        m.pan(-10000, 0);
        r = m.rect();
        check(near(r[0], 1000) && near(r[2], 2000), "pan stops at the right edge");
        m.pan(0, 500);
        check(near(m.rect()[1], 0) && near(m.rect()[3], 1000), "no vertical room at zoom 1");

        // zoom keeps the point under the finger, and never leaves the picture
        m = new CropMath(1000, 1000);
        m.frame(400, 400);
        m.zoomBy(2f, 100, -100);   // a point right of and above the centre
        r = m.rect();
        check(near(r[2] - r[0], 500) && near(r[3] - r[1], 500), "zoom 2 halves the crop");
        float px = 500 + 100 / 0.4f;   // the picture point under the finger before: scale 0.4
        float py = 500 - 100 / 0.4f;
        check(near(r[0] + (200 + 100) / 0.8f, px) && near(r[1] + (200 - 100) / 0.8f, py), "the point under the finger stays");
        m.zoomBy(100f, 0, 0);
        check(near(m.zoom(), CropMath.MAX_ZOOM), "zoom is capped");
        m.zoomBy(0.0001f, 0, 0);
        check(near(m.zoom(), 1f), "zoom never goes below 1");
        r = m.rect();
        check(near(r[0], 0) && near(r[2], 1000), "back at zoom 1 the picture fills the frame");

        // the crop always lies inside the picture
        m = new CropMath(640, 480);
        m.frame(300, 200);   // 3:2 frame on a 4:3 picture
        for (int i = 0; i < 50; i++) {
            m.zoomBy(i % 3 == 0 ? 1.3f : 0.8f, (i * 37) % 200 - 100, (i * 53) % 160 - 80);
            m.pan((i * 91) % 300 - 150, (i * 17) % 200 - 100);
            r = m.rect();
            check(r[0] >= -0.01f && r[1] >= -0.01f && r[2] <= 640.01f && r[3] <= 480.01f, "inside the picture at step " + i);
            check(near((r[2] - r[0]) / (r[3] - r[1]), 1.5f), "frame aspect kept at step " + i);
        }

        // the drawing position agrees with the rect: picture x = (frame x - left) / scale
        check(near((0 - m.left()) / m.scale(), m.rect()[0]) && near((300 - m.left()) / m.scale(), m.rect()[2]), "left() matches rect()");

        // output size: aspect of the frame, long side capped, small crops are not enlarged
        m = new CropMath(4000, 3000);
        m.frame(100, 100);
        int[] o = m.outputSize(1024);
        check(o[0] == 1024 && o[1] == 1024, "capped to 1024 " + o[0] + "x" + o[1]);
        m = new CropMath(500, 500);
        m.frame(100, 100);
        o = m.outputSize(1024);
        check(o[0] == 500 && o[1] == 500, "a small picture is not enlarged");
        // a frame resize keeps the crop valid
        m = new CropMath(1000, 500);
        m.frame(200, 200);
        m.zoomBy(3f, 0, 0);
        m.pan(-400, 0);
        m.frame(100, 400);
        r = m.rect();
        check(r[0] >= -0.01f && r[2] <= 1000.01f && r[1] >= -0.01f && r[3] <= 500.01f, "valid after a resize");

        if (fails > 0) { System.out.println(fails + " failed"); System.exit(1); }
        System.out.println("CropMathJvmTest ok");
    }
}
