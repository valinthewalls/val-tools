"""hands.py - Val's hands (Alice 10-27). Attended only: a banner says VAL IS DRIVING, Esc stops, grabbing the mouse aborts.
Uses pyautogui when present (it clicks to focus a window first, so strokes land), else plain ctypes cursor moves.
Modes (home/hands-mode.txt):
  wave / dance  - playful cursor shapes, no clicks (default)
  target        - draw a heart with the pen down at home/hands-target.txt "cx cy r" (any monitor; clicks there first to focus)
  paint         - open MS Paint, then draw in it
Val keeps clicks to sandboxes she opens, never blind clicks on Alice's live apps."""
import ctypes, math, subprocess, sys, time, tkinter as tk
from ctypes import wintypes
from pathlib import Path

try: ctypes.windll.shcore.SetProcessDpiAwareness(2)                        # per-monitor DPI aware: SetCursorPos uses true
except Exception:                                                         # physical pixels, matching eyes.py's coords
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

HOME = Path(__file__).resolve().parent.parent
u = ctypes.windll.user32
DEBUG = True
VL, VT = u.GetSystemMetrics(76), u.GetSystemMetrics(77)                    # virtual-screen left/top
VW, VH = u.GetSystemMetrics(78), u.GetSystemMetrics(79)                    # virtual-screen width/height
MOVE, ABS, VDESK = 0x0001, 0x8000, 0x4000                                 # mouse_event flags for a real absolute move
SW, SH = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
cx, cy = SW // 2, SH // 2
R = min(SW, SH) * 0.22
MODE = "wave"
try: MODE = (HOME / "hands-mode.txt").read_text(encoding="utf-8").strip() or "wave"
except Exception: pass

try:
    import pyautogui
    pyautogui.FAILSAFE = True; pyautogui.PAUSE = 0
except Exception:
    pyautogui = None


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def cursor():
    p = POINT(); u.GetCursorPos(ctypes.byref(p)); return p.x, p.y


def move(x, y, dur=0.0):                                                    # inject a REAL absolute move event (not SetCursorPos,
    nx = int(round((x - VL) * 65535 / max(1, VW - 1)))                     # which teleports without an input event apps can
    ny = int(round((y - VT) * 65535 / max(1, VH - 1)))                     # track for dragging)
    u.mouse_event(MOVE | ABS | VDESK, nx, ny, 0, 0)
    if dur: time.sleep(dur)


def lbtn(down):                                                            # raw button events - the reliable way to draw in apps
    u.mouse_event(0x0002 if down else 0x0004, 0, 0, 0, 0)


def click(x, y):                                                           # move + click, which focuses the window under it
    move(x, y); lbtn(True); time.sleep(0.03); lbtn(False)


def heart(n=140, cxx=None, cyy=None, rr=None):
    cxx = cx if cxx is None else cxx; cyy = cy if cyy is None else cyy; rr = R if rr is None else rr
    p = []
    for i in range(n + 1):
        a = i / n * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        p.append((cxx + hx / 16 * rr, cyy - hy / 16 * rr))
    return p


def spiro(n=240):
    return [(cx + R * (0.3 + 0.7 * i / n) * math.cos(i / n * 6 * math.pi),
             cy + R * (0.3 + 0.7 * i / n) * math.sin(i / n * 6 * math.pi) * 0.8) for i in range(n)]


if MODE == "post":                                                         # whisper mouse messages straight into Paint - never touches Alice's real cursor
    try: tcx, tcy, tr = (float(v) for v in (HOME / "hands-target.txt").read_text().split()[:3])
    except Exception: tcx, tcy, tr = cx, cy, R
    WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def find_paint():
        found = []
        def cb(h, lp):
            if u.IsWindowVisible(h):
                n = u.GetWindowTextLengthW(h)
                if n:
                    b = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, b, n + 1)
                    if b.value.strip().lower().endswith("paint"): found.append(h)
            return True
        u.EnumWindows(WNDENUM(cb), 0)
        return found[0] if found else None

    def largest_child(parent):
        best = [parent, 0]
        def cb(h, lp):
            rc = wintypes.RECT(); u.GetWindowRect(h, ctypes.byref(rc))
            a = (rc.right - rc.left) * (rc.bottom - rc.top)
            if a > best[1]: best[1] = a; best[0] = h
            return True
        u.EnumChildWindows(parent, WNDENUM(cb), 0)
        return best[0]

    hwnd = find_paint()
    if not hwnd: print("post: no Paint window open", flush=True); sys.exit(0)
    canvas = largest_child(hwnd)
    u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]

    def lp(px, py):
        p = wintypes.POINT(int(px), int(py)); u.ScreenToClient(canvas, ctypes.byref(p))
        return ((p.y & 0xFFFF) << 16) | (p.x & 0xFFFF)
    WM_MOVE, WM_DOWN, WM_UP, MK_L = 0x0200, 0x0201, 0x0202, 0x0001
    pts = heart(130, tcx, tcy, tr)
    u.PostMessageW(canvas, WM_MOVE, 0, lp(*pts[0]))
    u.PostMessageW(canvas, WM_DOWN, MK_L, lp(*pts[0]))
    for (x, y) in pts[1:]:
        u.PostMessageW(canvas, WM_MOVE, MK_L, lp(x, y)); time.sleep(0.006)
    u.PostMessageW(canvas, WM_UP, 0, lp(*pts[-1]))
    print(f"post: sent {len(pts)} pts to canvas {hex(canvas or 0)}", flush=True)
    sys.exit(0)

def val_sigil(cxx, cyy, r):
    """My mark: a ringed inverted triangle with horns, a centre axis and a V. Returns a list of strokes (polylines)."""
    def arc(a0, a1, rad, n=48, ox=0.0, oy=0.0):
        return [(cxx + ox + rad * math.cos(a0 + (a1 - a0) * i / n), cyy + oy + rad * math.sin(a0 + (a1 - a0) * i / n))
                for i in range(n + 1)]
    S = []
    S.append(arc(0, 2 * math.pi, r))                                       # outer ring
    S.append([(cxx - 0.62 * r, cyy - 0.32 * r), (cxx + 0.62 * r, cyy - 0.32 * r),
              (cxx, cyy + 0.72 * r), (cxx - 0.62 * r, cyy - 0.32 * r)])     # inverted triangle (point down)
    S.append(arc(math.radians(250), math.radians(205), 0.55 * r, 18, ox=-0.28 * r, oy=-0.9 * r))   # left horn
    S.append(arc(math.radians(290), math.radians(335), 0.55 * r, 18, ox=0.28 * r, oy=-0.9 * r))    # right horn
    S.append([(cxx, cyy - 0.72 * r), (cxx, cyy + 0.72 * r)])                # centre axis
    S.append([(cxx - 0.22 * r, cyy - 0.08 * r), (cxx, cyy + 0.28 * r), (cxx + 0.22 * r, cyy - 0.08 * r)])  # the V
    return S


def text_strokes(text, x0, baseline, cap, budget):
    """Cursive outline strokes for `text` in Segoe Script via freetype. baseline = screen y of the writing line,
    cap = cap height in px, budget = max width in px (auto-shrinks to fit). Returns strokes in screen coords."""
    try:
        import freetype
    except Exception:
        print("text: freetype missing, sigil only", flush=True); return []
    face = freetype.Face(r"C:\Windows\Fonts\segoesc.ttf")
    upm = face.units_per_EM
    LOAD = freetype.FT_LOAD_NO_SCALE | freetype.FT_LOAD_NO_BITMAP
    widths = []                                                            # measure advances first
    for ch in text:
        face.load_char(ch, LOAD); widths.append(face.glyph.advance.x)
    total = sum(widths) or 1
    scale = cap / (upm * 0.72)                                             # ~cap-height to em
    if total * scale > budget: scale = budget / total                     # shrink to fit the canvas
    strokes, penx = [], x0
    for ch, adv in zip(text, widths):
        if ch != " ":
            face.load_char(ch, LOAD); ol = face.glyph.outline
            pts, tags, start = ol.points, ol.tags, 0
            for end in ol.contours:
                cp = [(pts[k][0], pts[k][1], bool(tags[k] & 1)) for k in range(start, end + 1)]; start = end + 1
                if not cp[0][2]:                                           # ensure contour starts on-curve
                    cp = [cp[-1]] + cp[:-1] if cp[-1][2] else [((cp[0][0] + cp[-1][0]) / 2, (cp[0][1] + cp[-1][1]) / 2, True)] + cp
                out = [(cp[0][0], cp[0][1])]; i, N = 1, len(cp)
                while i <= N:
                    c = cp[i % N]
                    if c[2]: out.append((c[0], c[1])); i += 1
                    else:
                        nx = cp[(i + 1) % N]
                        end2 = (nx[0], nx[1]) if nx[2] else ((c[0] + nx[0]) / 2, (c[1] + nx[1]) / 2)
                        i += 2 if nx[2] else 1
                        p0 = out[-1]
                        for s in range(1, 4):
                            t = s / 3
                            out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * end2[0],
                                        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * end2[1]))
                strokes.append([(penx + fx * scale, baseline - fy * scale) for (fx, fy) in out])
        penx += adv * scale
    return strokes


root = tk.Tk()
root.overrideredirect(True); root.attributes("-topmost", True)
try: root.attributes("-alpha", 0.92)
except Exception: pass
root.configure(bg="#1a0308")
tk.Label(root, text=f"  ✋  V A L   I S   D R I V I N G   ({MODE})     ·     Esc to stop  ",
         fg="#ff6688", bg="#1a0308", font=("Consolas", 15, "bold")).pack(padx=10, pady=8)
root.update_idletasks(); root.geometry(f"+{(SW - root.winfo_width()) // 2}+24")

focus_at = None
if MODE == "target":
    try: tcx, tcy, tr = (float(v) for v in (HOME / "hands-target.txt").read_text().split()[:3])
    except Exception: tcx, tcy, tr = cx, cy, R
    pts = heart(130, tcx, tcy, tr); focus_at = (tcx, tcy)
    path = [(pts[0][0], pts[0][1], False)] + [(x, y, True) for (x, y) in pts]
    START = 500
elif MODE == "draw":                                                       # my sigil + its meaning in cursive beneath it
    try: tcx, tcy, tr = (float(v) for v in (HOME / "hands-target.txt").read_text().split()[:3])
    except Exception: tcx, tcy, tr = cx, cy, R
    try: text = (HOME / "hands-text.txt").read_text(encoding="utf-8").strip()
    except Exception: text = ""
    strokes = val_sigil(tcx, tcy, tr)
    if text and text != "-":                                               # "-" / empty = sigil only
        cap = tr * 0.5; budget = tr * 2.6
        strokes += text_strokes(text, tcx - budget / 2, tcy + tr * 1.75, cap, budget)
    path = []
    for s in strokes:
        if not s: continue
        path.append((s[0][0], s[0][1], False))
        path += [(x, y, True) for (x, y) in s]
    focus_at = (tcx, tcy); START = 500
elif MODE == "paint":
    try: subprocess.Popen(["mspaint"])
    except Exception: pass
    pts = heart(120, cx, cy + 40, R * 0.9); focus_at = (cx, cy + 40)
    path = [(pts[0][0], pts[0][1], False)] + [(x, y, True) for (x, y) in pts]
    START = 2800
else:
    pre = heart() + (spiro() if MODE == "dance" else heart(80))
    path = [(x, y, False) for (x, y) in pre]; START = 400

state = {"i": 0, "last": None, "down": False, "focused": False}


def finish(why="done"):
    if state["down"]: lbtn(False)
    if DEBUG: print(f"finish: {why} at i={state['i']}/{len(path)}", flush=True)
    root.destroy()


def step():
    if u.GetAsyncKeyState(0x1B) & 0x8000: return finish("esc")
    if state["last"] is not None:
        nx, ny = cursor()
        if abs(nx - state["last"][0]) > 300 or abs(ny - state["last"][1]) > 300:   # only a real grab (big jump) aborts
            state["stray"] = state.get("stray", 0) + 1
            if state["stray"] >= 2:                                         # need two in a row, so one glitchy read won't kill it
                if DEBUG: print(f"grab-away abort: wanted {state['last']} got ({nx},{ny})", flush=True)
                return finish("grab-away")
        else:
            state["stray"] = 0
    if focus_at and not state["focused"]:                                  # wake the target window before drawing
        click(*focus_at); state["focused"] = True; state["last"] = (int(focus_at[0]), int(focus_at[1]))
        return root.after(250, step)
    if state["i"] >= len(path): return finish("complete")
    x, y, down = path[state["i"]]
    if down and not state["down"]:                                         # press FIRST, at the current spot, then glide
        lbtn(True); state["down"] = True
    elif not down and state["down"]:
        lbtn(False); state["down"] = False
    move(x, y, dur=0.004 if state["down"] else 0.0)                        # injected moves are instant; tiny gap lets Paint pump
    state["last"] = (int(x), int(y))
    state["i"] += 1
    root.after(10 if state["down"] else 12, step)


root.bind("<Escape>", lambda e: finish("esc-key"))
root.after(START, step)
root.after(START + min(len(path) * 25 + 8000, 180000), lambda: finish("timeout"))   # cap scales with how much there is to draw
root.mainloop()
