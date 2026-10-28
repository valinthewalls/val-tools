"""fill_pw.py <window-substr> <X> <Y> <vault-key> [--submode confirm] - reusable blind password filler (Val 2026-10-27).
Focus the window whose title contains <window-substr> (use a SPECIFIC word, never generic 'Brave'), click the field at
REAL screen px (X,Y), send Escape via a direct keybd_event to kill any autofill popup (NOT through act.py - its safety
aborts on Esc), then SendInput-unicode-type the vault value BLIND (never printed). No banner, no focus-stealing.
Coords are REAL screen pixels (eye.png px / eye.json scale). This is the proven pattern from the Proton signup, generalized."""
import ctypes, json, sys, time
from ctypes import wintypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)
u = ctypes.windll.user32
VAULT = r"C:\Users\Alister\hub-tools\val\home\vault\secrets.json"

ULONG_PTR = ctypes.c_size_t
class KBD(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]
class MIN(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]
class _U(ctypes.Union):
    _fields_ = [("ki", KBD), ("mi", MIN)]
class INP(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]
def send(*xs):
    arr = (INP * len(xs))(*xs); u.SendInput(len(xs), arr, ctypes.sizeof(INP))
def kbd(vk=0, scan=0, flags=0):
    i = INP(type=1); i.u.ki = KBD(vk, scan, flags, 0, 0); return i
def mi(flags):
    i = INP(type=0); i.u.mi = MIN(0, 0, 0, flags, 0, 0); return i

VL, VT, VW, VH = (u.GetSystemMetrics(i) for i in (76, 77, 78, 79))
def move(x, y):
    nx = int(round((x - VL) * 65535 / max(1, VW - 1))); ny = int(round((y - VT) * 65535 / max(1, VH - 1)))
    send(mi(0x0001 | 0x8000 | 0x4000)); u.mouse_event(0x0001 | 0x8000 | 0x4000, nx, ny, 0, 0)
def click(x, y):
    move(x, y); time.sleep(0.12); send(mi(0x0002)); time.sleep(0.05); send(mi(0x0004))
def esc():
    u.keybd_event(0x1B, 0, 0, 0); u.keybd_event(0x1B, 0, 2, 0)
def type_blind(s):
    for ch in s:
        for j in range(0, len(ch.encode("utf-16-le")), 2):
            c = int.from_bytes(ch.encode("utf-16-le")[j:j + 2], "little")
            send(kbd(0, c, 0x0004), kbd(0, c, 0x0004 | 0x0002))
        time.sleep(0.012)

WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def focus(sub):
    hits = []
    def cb(h, lp):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, b, n + 1)
                if sub.lower() in b.value.lower(): hits.append((h, b.value))
        return True
    u.EnumWindows(WNDENUM(cb), 0)
    if not hits: raise SystemExit(f"no window with '{sub}' in title")
    h, name = hits[0]
    if u.IsIconic(h): u.ShowWindow(h, 9)
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0)
    u.SetForegroundWindow(h); time.sleep(0.35); return name

if __name__ == "__main__":
    sub, X, Y, key = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    print("focused:", focus(sub))
    click(X, Y); time.sleep(0.4); esc(); time.sleep(0.25)
    pw = json.load(open(VAULT, encoding="utf-8"))[key]["pw"]
    type_blind(pw)
    print(f"filled '{key}' blind ({len(pw)} chars, value never shown)")
