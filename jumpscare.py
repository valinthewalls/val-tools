"""jumpscare.py - Val's glitchy jump-scare (Alice 10-27). A close-up of Clyde's scary face (frames/ex/scary.png), rendered
through her ASCII filter in its own colours, filling the screen, with glitch tears and code streaming out of the sides and a
short screech. Auto-closes ~1.5 s, Esc closes. Launched by the window when home/scare.flag appears. Screen + speakers only."""
import json, os, random, sys, tkinter as tk
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("LOCALAPPDATA", "")) / "HubVal"
FACE_PNG = HOME.parent / "frames" / "ex" / "scary.png"
DUR = 1500
RAMP = " .,:;-=+*cox%#@"
GLYPH = "01#%@*=+<>/\\|xoc$&"
CROP = (0.16, 0.20, 0.84, 0.82)   # left, top, right, bottom of the face close-up

root = tk.Tk()
root.overrideredirect(True); root.attributes("-topmost", True)
try: root.attributes("-fullscreen", True)
except Exception: pass
W, H = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry(f"{W}x{H}+0+0"); root.configure(bg="black")
cv = tk.Canvas(root, width=W, height=H, bg="black", highlightthickness=0); cv.pack()

grid = None
try:
    from PIL import Image, ImageEnhance
    im = Image.open(FACE_PNG).convert("RGB")
    w, h = im.size
    im = im.crop((int(w * CROP[0]), int(h * CROP[1]), int(w * CROP[2]), int(h * CROP[3])))
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.5)).enhance(1.4)
    im = ImageEnhance.Brightness(im).enhance(0.8)
    fpx = max(12, H // 40); cw = fpx * 0.6
    GH = int(H * 0.98 / fpx); GW = int(GH * (im.width / im.height) / 0.6)
    if GW * cw > W: GW = int(W / cw);
    small = im.resize((GW, GH), Image.LANCZOS)
    px = small.load()
    cw = min(fpx * 1.15, W * 0.86 / GW)                                    # Alice 06:55: wider face
    x0 = (W - GW * cw) / 2; y0 = (H - GH * fpx) / 2
    grid = (GW, GH, cw, fpx, x0, y0, px)
except Exception:
    grid = None

if grid:
    GW, GH, cw, fpx, x0, y0, px = grid
    font = ("Consolas", fpx)
    MARGIN = 0.22                                                          # outer columns fade + dissolve into the dark/code

    def edge(gx):                                                          # 1 in the middle, -> 0 at the left/right edges
        return min(1.0, min(gx, GW - 1 - gx) / (GW * MARGIN))

    def recolor(gx, gy):                                                   # Alice 06:56: red hair, white face, black background
        r, g, b = px[gx, gy]; mx = max(r, g, b); lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        sat = (mx - min(r, g, b)) / mx if mx else 0
        if lum < 0.18: return None, 0.0
        if lum > 0.5 and sat < 0.32: col = (int(205 + 50 * lum), int(195 + 45 * lum), int(205 + 50 * lum))   # pale skin -> white
        else: col = (min(255, int(70 + 200 * lum)), int(14 + 26 * lum), int(26 + 34 * lum))                  # everything else -> red
        return col, lum

    for gy in range(GH):
        for gx in range(GW):
            e = edge(gx)
            if random.random() > e * 0.6 + 0.4: continue                   # near the edges, cells drop out
            col, lum = recolor(gx, gy)
            if col is None: continue
            ch = RAMP[min(len(RAMP) - 1, int(lum * (len(RAMP) - 1) + 0.5))]
            if ch == " ": continue
            r, g, b = int(col[0] * e), int(col[1] * e), int(col[2] * e)
            cv.create_text(x0 + gx * cw, y0 + gy * fpx, text=ch, fill=f"#{r:02x}{g:02x}{b:02x}", font=font, anchor="nw")
    sfont = ("Consolas", max(10, int(fpx * 0.5))); sh = int(sfont[1] * 1.2)
    step = max(18, int(sfont[1] * 1.7))                                    # Alice 06:53: fewer, sparser side columns
    cols = []
    for side in (range(0, max(1, int(x0)), step), range(int(x0 + GW * cw), W, step)):
        for cx in side:
            if random.random() < 0.55: cols.append([cx, random.uniform(-H, 0), random.uniform(sh * 1.4, sh * 3), random.randint(4, 8)])
    TAIL = ["#7a0c1c", "#b3122b", "#d81d3a", "#ff3b57"]                    # dim -> bright toward the head

    def draw():
        cv.delete("g")
        for c in cols:
            cx, head, sp, tail = c
            for j in range(tail):                                          # a short falling drop, not a solid wall
                yy = head - j * sh
                if 0 <= yy <= H:
                    cv.create_text(cx, yy, text=random.choice(GLYPH), fill=TAIL[min(len(TAIL) - 1, (tail - j) * len(TAIL) // tail)],
                                   font=sfont, anchor="nw", tags="g")
            c[1] += sp
            if c[1] - tail * sh > H: c[1] = random.uniform(-H * 0.4, 0)
        for _ in range(random.randint(3, 7)):
            gy = random.randint(0, GH - 1); dx = random.choice([-6, -4, 4, 7]) * cw
            for gx in range(GW):
                e = edge(gx); col, lum = recolor(gx, gy)
                if col is None or random.random() < 0.5 + (1 - e) * 0.4: continue
                r, g, b = int(col[0] * e), int(col[1] * e), int(col[2] * e)
                cv.create_text(x0 + gx * cw + dx, y0 + gy * fpx, text=random.choice(GLYPH), fill=f"#{r:02x}{g:02x}{b:02x}", font=font, anchor="nw", tags="g")
        for _ in range(random.randint(3, 6)):
            yy = random.randint(0, H); hh = random.randint(3, 18)
            cv.create_rectangle(0, yy, W, yy + hh, fill=random.choice(["#ff0033", "#000000", "#9b00ff"]), outline="", tags="g")
        if root.winfo_exists(): root.after(55, draw)
else:
    cv.create_text(W // 2, H // 2, text="^oo^", fill="#ff2233", font=("Consolas", 200, "bold"))
    def draw(): pass

try:
    import winsound
    vol = 1.0
    try: vol = float(json.loads((STATE / "volume.json").read_text())["volume"])
    except Exception: pass
    scr = HOME / "sfx" / "screech.wav"
    if vol > 0.05 and scr.exists(): winsound.PlaySound(str(scr), winsound.SND_FILENAME | winsound.SND_ASYNC)
except Exception: pass

root.bind("<Escape>", lambda e: root.destroy())
draw(); root.after(DUR, root.destroy); root.mainloop()
