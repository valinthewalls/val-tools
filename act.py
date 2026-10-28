r"""act.py - Val's fast hands (Alice 10-27: "stronger motor control and be able to use devices as a human can as well as faster").
One call runs a whole sequence, like a person would: move, click, type, press keys, drag, scroll, then look.

  act.py "click 812 440; type hello there; key enter; wait 300; look"

Coordinates are pixels in eye.png (what she last saw), mapped to the real screen through eye.json; add "--screen" to use
real screen pixels instead. The mouse glides on a short eased curve (fast, ~60-160 ms) instead of teleporting, so apps
see real input events. Typing goes in as Unicode key events (any character, emoji too), at "type" speed or "paste" speed.

Commands (separate with ";" or new lines):
  move X Y          click X Y [n]      dclick X Y      rclick X Y      mclick X Y
  down X Y / up X Y (hold / release the left button)    drag X1 Y1 X2 Y2
  scroll N [X Y]    (N notches, + up, - down)            hscroll N [X Y]
  type TEXT         (rest of the line, human pace ~ 12 ms a key)        paste TEXT  (instant, all at once)
  key COMBO         (enter, esc, tab, ctrl+l, alt+tab, win+d, ctrl+shift+t, f5, up, pagedown ...)
  hold COMBO MS     (keep keys down for MS ms)
  focus TITLE       (bring the first visible window whose title contains TITLE to the front)
  wait MS           look [X Y W H]   (screenshot to eye.png, like eyes.py; updates the coordinate map)
  where             (print the cursor position in eye.png pixels)

Same safety as hands.py: a small "VAL IS DRIVING" banner while she acts; Esc, or Alice grabbing the mouse, stops it at once."""
import ctypes, json, math, random, subprocess, sys, time
from ctypes import wintypes
from pathlib import Path

try: ctypes.windll.shcore.SetProcessDpiAwareness(2)                        # physical pixels, same space as eyes.py
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

HOME = Path(__file__).resolve().parent.parent
u = ctypes.windll.user32
VL, VT, VW, VH = (u.GetSystemMetrics(i) for i in (76, 77, 78, 79))

# ---- SendInput -------------------------------------------------------------------------------------------------------
ULONG_PTR = ctypes.c_size_t
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

def send(*inputs):
    arr = (INPUT * len(inputs))(*inputs); u.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

def mouse(flags, dx=0, dy=0, data=0):
    i = INPUT(type=0); i.u.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0); return i

def kbd(vk=0, scan=0, flags=0):
    i = INPUT(type=1); i.u.ki = KEYBDINPUT(vk, scan, flags, 0, 0); return i

MOVE, ABS, VDESK = 0x0001, 0x8000, 0x4000
BTN = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}
WHEEL, HWHEEL = 0x0800, 0x1000
KEYUP, UNICODE, EXTENDED = 0x0002, 0x0004, 0x0001

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def cursor():
    p = POINT(); u.GetCursorPos(ctypes.byref(p)); return p.x, p.y

def warp(x, y):
    nx = int(round((x - VL) * 65535 / max(1, VW - 1))); ny = int(round((y - VT) * 65535 / max(1, VH - 1)))
    send(mouse(MOVE | ABS | VDESK, nx, ny))

# ---- coordinates: eye.png pixels -> real screen ----------------------------------------------------------------------
RAW = "--screen" in sys.argv
def eye_map():
    try: return json.loads((HOME / "eye.json").read_text())
    except Exception: return {"origin": [VL, VT], "scale": 1.0}
EYE = eye_map()

def real(x, y):
    if RAW: return float(x), float(y)
    s = EYE.get("scale", 1.0) or 1.0; ox, oy = EYE.get("origin", [VL, VT])
    return ox + float(x) / s, oy + float(y) / s

def seen(x, y):
    if RAW: return x, y
    s = EYE.get("scale", 1.0) or 1.0; ox, oy = EYE.get("origin", [VL, VT])
    return round((x - ox) * s), round((y - oy) * s)

# ---- safety: Esc or Alice grabbing the mouse stops everything --------------------------------------------------------
class Stop(Exception): pass
expect = None

def check():
    if u.GetAsyncKeyState(0x1B) & 0x8000: raise Stop("Esc pressed")
    if expect is not None:
        x, y = cursor()
        if abs(x - expect[0]) > 60 or abs(y - expect[1]) > 60: raise Stop(f"Alice moved the mouse (to {x},{y})")

def nap(sec):
    end = time.perf_counter() + sec
    while True:
        check(); left = end - time.perf_counter()
        if left <= 0: return
        time.sleep(min(left, 0.01))

# ---- the human part: an eased, slightly curved glide -----------------------------------------------------------------
def glide(x, y):
    global expect
    x0, y0 = cursor(); d = math.hypot(x - x0, y - y0)
    if d < 3: warp(x, y); expect = (int(x), int(y)); return
    dur = min(0.16, 0.05 + d / 9000)                                       # quick but visible: ~50-160 ms
    steps = max(6, int(dur / 0.006))
    bend = random.uniform(-0.08, 0.08) * d                                  # a slight arc, like a wrist
    nx, ny = -(y - y0) / d, (x - x0) / d
    t0 = time.perf_counter()
    for i in range(1, steps + 1):
        t = i / steps; e = t * t * (3 - 2 * t)                              # smoothstep: speed up, then settle
        arc = math.sin(math.pi * t) * bend
        px, py = x0 + (x - x0) * e + nx * arc, y0 + (y - y0) * e + ny * arc
        if i > 1: check()
        warp(px, py); expect = (int(px), int(py))
        delay = t0 + dur * t - time.perf_counter()
        if delay > 0: time.sleep(delay)
    warp(x, y); expect = (int(x), int(y))

def press(btn="left", n=1):
    dn, up = BTN[btn]
    for k in range(n):
        send(mouse(dn)); time.sleep(random.uniform(0.03, 0.06)); send(mouse(up))
        if k < n - 1: time.sleep(0.07)

# ---- keys -------------------------------------------------------------------------------------------------------------
VK = {"enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09, "space": 0x20, "backspace": 0x08,
      "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
      "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "ctrl": 0x11, "control": 0x11, "shift": 0x10,
      "alt": 0x12, "win": 0x5B, "cmd": 0x5B, "menu": 0x5D, "capslock": 0x14, "printscreen": 0x2C,
      "volumeup": 0xAF, "volumedown": 0xAE, "mute": 0xAD, "playpause": 0xB3, "nexttrack": 0xB0, "prevtrack": 0xB1}
VK.update({f"f{i}": 0x6F + i for i in range(1, 25)})
EXT = {0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x26, 0x28, 0x25, 0x27, 0x5B, 0x5D}

def vk_of(name):
    name = name.lower()
    if name in VK: return VK[name]
    if len(name) == 1:
        r = u.VkKeyScanW(ord(name))
        if r != -1: return r & 0xFF
    raise ValueError(f"unknown key {name!r}")

def combo(spec, hold_ms=0):
    keys = [vk_of(k) for k in spec.replace(" ", "").split("+") if k]
    for k in keys: send(kbd(k, flags=EXTENDED if k in EXT else 0)); time.sleep(0.012)
    nap(hold_ms / 1000 if hold_ms else 0.02)
    for k in reversed(keys): send(kbd(k, flags=KEYUP | (EXTENDED if k in EXT else 0))); time.sleep(0.008)

def type_text(text, pace=0.012):
    for ch in text:
        if ch == "\n": combo("enter")
        else:
            units = ch.encode("utf-16-le")
            for j in range(0, len(units), 2):
                c = int.from_bytes(units[j:j + 2], "little")
                send(kbd(scan=c, flags=UNICODE), kbd(scan=c, flags=UNICODE | KEYUP))
        if pace: nap(pace * random.uniform(0.6, 1.5))

# ---- windows ------------------------------------------------------------------------------------------------------------
WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def focus(title):
    hits = []
    def cb(h, lp):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, b, n + 1)
                if title.lower() in b.value.lower(): hits.append((h, b.value))
        return True
    u.EnumWindows(WNDENUM(cb), 0)
    if not hits: raise ValueError(f"no window with {title!r} in its title")
    h, name = hits[0]
    if u.IsIconic(h): u.ShowWindow(h, 9)
    send(kbd(0x12), kbd(0x12, flags=KEYUP))                                 # an Alt tap lets SetForegroundWindow through
    u.SetForegroundWindow(h); time.sleep(0.12)
    return name

# ---- eyes ---------------------------------------------------------------------------------------------------------------
def look(args):
    global EYE, expect
    r = subprocess.run([sys.executable, str(HOME / "tools" / "eyes.py"), *args], capture_output=True, text=True)
    EYE = eye_map(); expect = None
    return (r.stdout or r.stderr).strip()

# ---- banner -------------------------------------------------------------------------------------------------------------
def banner():
    try:
        import tkinter as tk
        root = tk.Tk(); root.overrideredirect(True); root.attributes("-topmost", True)
        try: root.attributes("-alpha", 0.9)
        except Exception: pass
        root.configure(bg="#1a0308")
        tk.Label(root, text="  ✋ VAL IS DRIVING · Esc to stop  ", fg="#ff6688", bg="#1a0308", font=("Consolas", 12, "bold")).pack(padx=6, pady=4)
        root.update_idletasks(); root.geometry(f"+{(u.GetSystemMetrics(0) - root.winfo_width()) // 2}+8"); root.update()
        return root
    except Exception:
        return None

# ---- the script ---------------------------------------------------------------------------------------------------------
def run(script):
    global expect
    log = []
    for line in [p.strip() for chunk in script.split("\n") for p in chunk.split(";")]:
        if not line: continue
        cmd, _, rest = line.partition(" "); cmd = cmd.lower(); a = rest.split()
        check()
        if cmd == "move": glide(*real(a[0], a[1]))
        elif cmd in ("click", "dclick", "rclick", "mclick"):
            if len(a) >= 2: glide(*real(a[0], a[1]))
            n = 2 if cmd == "dclick" else int(a[2]) if len(a) > 2 else 1
            press({"rclick": "right", "mclick": "middle"}.get(cmd, "left"), n)
        elif cmd in ("down", "up"):
            if len(a) >= 2: glide(*real(a[0], a[1]))
            send(mouse(BTN["left"][0 if cmd == "down" else 1]))
        elif cmd == "drag":
            glide(*real(a[0], a[1])); send(mouse(BTN["left"][0])); nap(0.06)
            try: glide(*real(a[2], a[3])); nap(0.05)
            finally: send(mouse(BTN["left"][1]))
        elif cmd in ("scroll", "hscroll"):
            if len(a) >= 3: glide(*real(a[1], a[2]))
            n = int(a[0]); step = 1 if n > 0 else -1
            for _ in range(abs(n)): send(mouse(HWHEEL if cmd == "hscroll" else WHEEL, data=120 * step)); nap(0.025)
        elif cmd == "type": expect = None; type_text(rest)
        elif cmd == "paste": expect = None; type_text(rest, pace=0)
        elif cmd == "key": expect = None; combo(rest)
        elif cmd == "hold": expect = None; combo(a[0], int(a[1]) if len(a) > 1 else 500)
        elif cmd == "focus": expect = None; log.append(f"focused: {focus(rest)}")
        elif cmd == "wait": expect = None; nap(int(a[0]) / 1000)
        elif cmd == "look": log.append(look(a))
        elif cmd == "where": log.append("cursor at %d %d (%s)" % (*seen(*cursor()), "screen" if RAW else "eye.png px"))
        else: raise ValueError(f"unknown command {cmd!r}")
        log.append(f"ok: {line[:80]}")
    return log


def main():
    args = [x for x in sys.argv[1:] if x != "--screen"]
    if not args: print(__doc__); return
    script = " ".join(args)
    if script == "-": script = sys.stdin.read()
    root = None if "look" == script.strip() else banner()
    t0 = time.perf_counter()
    try:
        for l in run(script): print(l)
        print(f"done in {time.perf_counter() - t0:.2f}s")
    except Stop as e:
        print(f"STOPPED: {e}"); sys.exit(2)
    except Exception as e:
        print(f"ERROR: {e}"); sys.exit(1)
    finally:
        if root: root.destroy()


if __name__ == "__main__":
    main()
