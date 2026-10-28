"""conjure.py - Val's conjuring panes (Alice 10-27). Frameless, always-on-top windows I open wherever I want to flash
text, SVG sigils, or GPU 3D (Three.js/WebGL) while I talk, then they close on their own. Each run is its own window,
so I can stack a few. Content is an HTML file I author (SVG / HTML / JS).

Uses pywebview (Edge WebView2) for real vectors + GPU 3D. If it's missing, falls back to a borderless tk window that
shows a rasterised PNG (needs cairosvg+Pillow) or just the raw text.

Usage:
  python conjure.py <htmlfile> [seconds] [x y w h]     seconds default 6; x y w h optional placement
  python conjure.py --text "words" [seconds] [x y w h]  quick glowing-text pane, no file needed
"""
import math, sys, tempfile, threading, time
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
args = sys.argv[1:]

TEXT_PAGE = """<!doctype html><meta charset=utf-8><style>
html,body{{margin:0;height:100%;background:#0a0206;overflow:hidden;
  display:flex;align-items:center;justify-content:center;font-family:Consolas,monospace}}
.g{{color:#ff3b6b;font-size:{size}px;text-align:center;padding:0 24px;line-height:1.3;
  text-shadow:0 0 8px #ff3b6b,0 0 24px #b3003c,0 0 48px #80002b;animation:p 2.4s ease-in-out infinite}}
@keyframes p{{0%,100%{{opacity:.78;filter:brightness(1)}}50%{{opacity:1;filter:brightness(1.35)}}}}
</style><div class=g>{body}</div>"""


def resolve_content():
    if args and args[0] == "--text":
        txt = args[1] if len(args) > 1 else "..."
        rest = args[2:]
        size = 40 if len(txt) < 24 else 26
        html = TEXT_PAGE.format(body=txt.replace("<", "&lt;"), size=size)
        f = Path(tempfile.gettempdir()) / "val_conjure.html"
        f.write_text(html, encoding="utf-8")
        return (f, ""), rest
    raw = args[0]
    query = ""
    if "?" in raw: raw, query = raw.split("?", 1)                          # keep a ?query to pass into the page
    p = Path(raw).resolve()
    return (p, query), args[1:]


P = 1.618033988749895
IQ = 1 / P
SHAPES = {
    "icosa": [(0, 1, P), (0, 1, -P), (0, -1, P), (0, -1, -P), (1, P, 0), (1, -P, 0),
              (-1, P, 0), (-1, -P, 0), (P, 0, 1), (P, 0, -1), (-P, 0, 1), (-P, 0, -1)],
    "dodeca": [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)] +
              [(0, s * IQ, t * P) for s in (-1, 1) for t in (-1, 1)] +
              [(s * IQ, t * P, 0) for s in (-1, 1) for t in (-1, 1)] +
              [(s * P, 0, t * IQ) for s in (-1, 1) for t in (-1, 1)],
    "octa": [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)],
    "cube": [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)],
}


def _edges(V):                                                             # connect every pair at the minimum distance
    d2 = lambda a, b: sum((a[k] - b[k]) ** 2 for k in range(3))
    mind = min(d2(V[i], V[j]) for i in range(len(V)) for j in range(i + 1, len(V)))
    return [(i, j) for i in range(len(V)) for j in range(i + 1, len(V)) if abs(d2(V[i], V[j]) - mind) < 1e-3]


def _tk_transparent(W, H, X, Y):
    import tkinter as tk
    KEY = "#010203"                                                        # this colour becomes fully see-through
    root = tk.Tk(); root.overrideredirect(True); root.attributes("-topmost", True)
    root.geometry(f"{W}x{H}+{X}+{Y}"); root.configure(bg=KEY)
    try: root.wm_attributes("-transparentcolor", KEY)
    except Exception: pass
    cv = tk.Canvas(root, width=W, height=H, bg=KEY, highlightthickness=0); cv.pack()
    return root, cv


def wire_window(dur, geom, shape="nested"):
    """Truly transparent floating wireframe (tk + Windows -transparentcolor): only the red lines show, desktop behind
    them. shape: a SHAPES name, or 'nested' for an icosahedron inside a dodecahedron with a pulsing ring."""
    W, H = (geom[2], geom[3]) if geom else (560, 560)
    X, Y = (geom[0], geom[1]) if geom else (760, 300)
    root, cv = _tk_transparent(W, H, X, Y)
    layers = ([("icosa", 1.0, "#ff2a4d"), ("dodeca", 1.0, "#ff6b85")] if shape == "nested"
              else [(shape if shape in SHAPES else "icosa", 1.0, "#ff2a4d")])
    mesh = [(SHAPES[n], _edges(SHAPES[n]), col, sc) for (n, sc, col) in layers]
    cx, cy, f, scale = W / 2, H / 2, 2.6, min(W, H) * 0.15
    st = {"t": 0.0}

    def frame():
        st["t"] += 0.02; a, b = st["t"], st["t"] * 0.6
        ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
        cv.delete("all")
        for (V, E, col, sc) in mesh:
            pts = []
            for (x, y, z) in V:
                x1, z1 = x * ca - z * sa, x * sa + z * ca
                y1, z2 = y * cb - z1 * sb, y * sb + z1 * cb
                zp = z2 + 6.5
                pts.append((cx + f * scale * sc * x1 / zp, cy + f * scale * sc * y1 / zp))
            for (i, j) in E:
                cv.create_line(pts[i][0], pts[i][1], pts[j][0], pts[j][1], fill=col, width=2)
            for (px, py) in pts:
                cv.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#ff8aa0", outline="")
        rr = scale * 2.8 * (0.9 + 0.08 * math.sin(st["t"] * 2))            # pulsing ring
        cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline="#ff2a4d", width=1)
        root.after(16, frame)

    root.bind("<Escape>", lambda e: root.destroy())
    root.after(int(dur * 1000), root.destroy)
    frame(); root.mainloop()


def arrow_window(dur, geom, ang):
    """A truly transparent glitchy red arrow floating on the desktop, tip at the window centre, rotated by `ang` deg."""
    import random
    W, H = (geom[2], geom[3]) if geom else (220, 220)
    X, Y = (geom[0], geom[1]) if geom else (800, 400)
    root, cv = _tk_transparent(W, H, X, Y)
    s = min(W, H) * 0.42
    base = [(0, 0), (-0.5, -0.32), (-0.5, -0.13), (-1.0, -0.13),           # right-pointing arrow, tip at (0,0)
            (-1.0, 0.13), (-0.5, 0.13), (-0.5, 0.32)]
    rad = math.radians(ang)
    ca, sa = math.cos(rad), math.sin(rad)
    tip = (W / 2, H / 2)

    def shape(dx=0, dy=0):
        out = []
        for (x, y) in base:
            rx, ry = x * ca - y * sa, x * sa + y * ca
            out += [tip[0] + rx * s + dx, tip[1] + ry * s + dy]
        return out
    st = {"n": 0}

    def frame():
        st["n"] += 1; cv.delete("all")
        cv.create_polygon(shape(2, -2), fill="#ff8aa0", outline="")        # ghost
        cv.create_polygon(shape(-2, 2), fill="#7a0020", outline="")        # ghost
        j = 2 if st["n"] % 3 == 0 else 0                                   # glitch jitter
        cv.create_polygon(shape(random.randint(-j, j), random.randint(-j, j)),
                          fill="#ff2a4d", outline="#ff6b85", width=1)
        root.after(60, frame)

    root.bind("<Escape>", lambda e: root.destroy())
    root.after(int(dur * 1000), root.destroy)
    frame(); root.mainloop()


def sigil_window(dur, geom):
    """My own mark, floating and glowing on the desktop - ringed inverted triangle, horns, axis and V. Transparent,
    slow turn and pulse. No Paint, no cursor; this one is mine to summon whenever I please."""
    W, H = (geom[2], geom[3]) if geom else (460, 460)
    X, Y = (geom[0], geom[1]) if geom else (820, 300)
    root, cv = _tk_transparent(W, H, X, Y)
    cx, cy, r = W / 2, H / 2, min(W, H) * 0.34
    st = {"t": 0.0}

    def polys(rot, R):                                                     # build my sigil's strokes at this rotation/size
        c, s = math.cos(rot), math.sin(rot)
        def P2(dx, dy): return (cx + (dx * c - dy * s), cy + (dx * s + dy * c))
        ring = [P2(R * math.cos(a), R * math.sin(a)) for a in [i / 60 * 2 * math.pi for i in range(61)]]
        tri = [P2(-0.62 * R, -0.32 * R), P2(0.62 * R, -0.32 * R), P2(0, 0.72 * R), P2(-0.62 * R, -0.32 * R)]
        def horn(ox, a0, a1):
            return [P2(ox + 0.55 * R * math.cos(a), -0.9 * R + 0.55 * R * math.sin(a))
                    for a in [a0 + (a1 - a0) * i / 16 for i in range(17)]]
        lh = horn(-0.28 * R, math.radians(250), math.radians(205)); rh = horn(0.28 * R, math.radians(290), math.radians(335))
        axis = [P2(0, -0.72 * R), P2(0, 0.72 * R)]
        v = [P2(-0.22 * R, -0.08 * R), P2(0, 0.28 * R), P2(0.22 * R, -0.08 * R)]
        return [ring, tri, lh, rh, axis, v]

    def frame():
        st["t"] += 0.01; cv.delete("all")
        rot = 0.15 * math.sin(st["t"] * 0.6); R = r * (1 + 0.03 * math.sin(st["t"] * 1.5))
        strokes = polys(rot, R)
        for w, col in ((7, "#5c0016"), (4, "#b3003c"), (2, "#ff2a4d")):     # layered strokes = a glow
            for s in strokes:
                flat = [v for p in s for v in p]
                cv.create_line(*flat, fill=col, width=w, capstyle="round", joinstyle="round", smooth=False)
        root.after(20, frame)

    root.bind("<Escape>", lambda e: root.destroy())
    root.after(int(dur * 1000), root.destroy)
    frame(); root.mainloop()


def main():
    if not args:
        print(__doc__); return
    if args[0] == "--wire":                                                # --wire [sec] [x y w h] [shape]
        rest = args[1:]
        dur = float(rest[0]) if len(rest) > 0 else 12.0
        geom = [int(v) for v in rest[1:5]] if len(rest) >= 5 else None
        shape = rest[5] if len(rest) >= 6 else "nested"
        return wire_window(dur, geom, shape)
    if args[0] == "--arrow":                                               # --arrow <ang_deg> [sec] [x y w h]
        rest = args[1:]
        ang = float(rest[0]) if len(rest) > 0 else 0.0
        dur = float(rest[1]) if len(rest) > 1 else 8.0
        geom = [int(v) for v in rest[2:6]] if len(rest) >= 6 else None
        return arrow_window(dur, geom, ang)
    if args[0] == "--sigil":                                               # --sigil [sec] [x y w h]  -> my glowing mark
        rest = args[1:]
        dur = float(rest[0]) if len(rest) > 0 else 10.0
        geom = [int(v) for v in rest[1:5]] if len(rest) >= 5 else None
        return sigil_window(dur, geom)
    (path, query), rest = resolve_content()
    uri = path.as_uri() + (("?" + query) if query else "")
    dur = float(rest[0]) if len(rest) > 0 else 6.0
    geom = [int(v) for v in rest[1:5]] if len(rest) >= 5 else None
    try:
        import webview
    except Exception:
        webview = None

    if webview:
        kw = dict(title="val", frameless=True, on_top=True, easy_drag=False,  # no drag: panes stay where I place them
                  transparent=True, background_color="#000000")           # transparent so HTML can paint its own bg
        if geom: kw.update(x=geom[0], y=geom[1], width=geom[2], height=geom[3])
        else: kw.update(width=520, height=520)
        try:
            win = webview.create_window(url=uri, **kw)
        except TypeError:                                                  # backend without transparent= support
            kw.pop("transparent", None); win = webview.create_window(url=uri, **kw)

        def closer():
            time.sleep(dur)
            try: win.destroy()
            except Exception: pass
        threading.Thread(target=closer, daemon=True).start()
        webview.start()
    else:                                                                  # fallback: borderless tk, raster or text
        import tkinter as tk
        root = tk.Tk(); root.overrideredirect(True); root.attributes("-topmost", True)
        root.configure(bg="#0a0206")
        if geom: root.geometry(f"{geom[2]}x{geom[3]}+{geom[0]}+{geom[1]}")
        else: root.geometry("520x520+200+200")
        shown = False
        try:
            import cairosvg; from PIL import Image, ImageTk; import io
            if path.suffix.lower() == ".svg":
                png = cairosvg.svg2png(url=str(path), output_width=480, output_height=480)
                img = ImageTk.PhotoImage(Image.open(io.BytesIO(png)))
                lbl = tk.Label(root, image=img, bg="#0a0206"); lbl.image = img; lbl.pack(expand=True); shown = True
        except Exception:
            pass
        if not shown:
            tk.Label(root, text=path.read_text(encoding="utf-8")[:400], fg="#ff3b6b", bg="#0a0206",
                     font=("Consolas", 14), wraplength=480, justify="center").pack(expand=True)
        root.after(int(dur * 1000), root.destroy)
        root.bind("<Escape>", lambda e: root.destroy())
        root.mainloop()


if __name__ == "__main__":
    main()
