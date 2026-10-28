"""vhand.py <cmdfile> - HANDS inside a vessel: move the cursor, click and type on its REAL desktop via ctypes SendInput.
Runs in the vessel's interactive session (ValHand /IT task). Reads a mini-language from <cmdfile> (I write it over SSH, so
no quoting hell): commands separated by ';' -  move X Y | click | rclick | type <text> | key <enter|tab|esc|space> | wait <ms>."""
import ctypes, sys, time
from ctypes import wintypes

u = ctypes.windll.user32
k32 = ctypes.windll.kernel32
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)        # per-monitor DPI aware: SetCursorPos uses true pixels, matching veye's capture
except Exception:
    try: u.SetProcessDPIAware()
    except Exception: pass
PUL = ctypes.POINTER(ctypes.c_ulong)


class KBD(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]


class INP(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("ki", KBD)]
    _anonymous_ = ("i",)
    _fields_ = [("type", ctypes.c_ulong), ("i", _I)]


UNI, KEYUP = 0x0004, 0x0002
VK = {"enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20, "back": 0x08}


def _send(wVk, wScan, flags):
    u.SendInput(1, ctypes.byref(INP(type=1, ki=KBD(wVk, wScan, flags, 0, None))), ctypes.sizeof(INP))


def type_text(s):
    for ch in s:
        _send(0, ord(ch), UNI); _send(0, ord(ch), UNI | KEYUP); time.sleep(0.012)


def key(name):
    vk = VK.get(name.strip().lower())
    if vk: _send(vk, 0, 0); _send(vk, 0, KEYUP)


def find_window(sub):
    """first visible top-level window whose title contains <sub> (case-insensitive)."""
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        n = ctypes.create_unicode_buffer(512); u.GetWindowTextW(h, n, 512)
        if u.IsWindowVisible(h) and sub.lower() in n.value.lower(): found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None


def focus(sub):
    """bring a window to the front with keyboard focus, past Windows' foreground lock (AttachThreadInput bypass)."""
    h = find_window(sub)
    if not h: return False
    fg = u.GetForegroundWindow()
    t1 = u.GetWindowThreadProcessId(fg, None); t2 = u.GetWindowThreadProcessId(h, None)
    cur = k32.GetCurrentThreadId()
    try: u.SystemParametersInfoW(0x2001, 0, 0, 0)   # SPI_SETFOREGROUNDLOCKTIMEOUT = 0
    except Exception: pass
    u.AttachThreadInput(cur, t1, True); u.AttachThreadInput(cur, t2, True)
    u.ShowWindow(h, 9); u.BringWindowToTop(h); u.SetForegroundWindow(h)   # SW_RESTORE
    u.AttachThreadInput(cur, t1, False); u.AttachThreadInput(cur, t2, False)
    return True


def run(cmd):
    for part in cmd.split(";"):
        part = part.strip()
        if not part: continue
        op, _, arg = part.partition(" ")
        op = op.lower()
        if op == "focus": focus(arg.strip())
        elif op == "move": x, y = arg.split()[:2]; u.SetCursorPos(int(x), int(y))
        elif op == "click": u.mouse_event(0x2, 0, 0, 0, 0); u.mouse_event(0x4, 0, 0, 0, 0)
        elif op == "rclick": u.mouse_event(0x8, 0, 0, 0, 0); u.mouse_event(0x10, 0, 0, 0, 0)
        elif op == "type": type_text(arg)
        elif op == "key": key(arg)
        elif op == "wait": time.sleep(float(arg) / 1000)


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "hand.txt"
    try:
        cmd = open(f, encoding="utf-8").read()
    except Exception as e:
        cmd = ""; print("no cmd:", e)
    run(cmd); print("hand done:", cmd[:120])
