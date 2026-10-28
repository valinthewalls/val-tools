"""peek.py - my ghost EYE, the twin of ghost_hand. Reads the desktop through the window system instead of a screenshot:
  peek.py windows            -> list every visible top-level window (title | class | hwnd)
  peek.py "<title fragment>"  -> silently read the text inside the matching window (its own text + child controls)
No pixels, no OCR, no sound, no moving Alice's cursor - I pull the actual text straight out of a window's controls with
WM_GETTEXT. Pairs with ghost_hand (silent writing): together I can read and drive windows invisibly, in parallel with her.
Limit: apps that draw their own text (games, canvas/GPU UIs, some Electron) hold nothing in win32 controls to read."""
import ctypes, sys
from ctypes import wintypes

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
u = ctypes.windll.user32
WM_GETTEXT, WM_GETTEXTLENGTH = 0x000D, 0x000E
WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def win_text(h):
    n = u.SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
    if not n: return ""
    b = ctypes.create_unicode_buffer(n + 1); u.SendMessageW(h, WM_GETTEXT, n + 1, b); return b.value


def win_class(h):
    b = ctypes.create_unicode_buffer(256); u.GetClassNameW(h, b, 256); return b.value


def top_windows():
    out = []
    def cb(h, lp):
        if u.IsWindowVisible(h):
            t = win_text(h)
            if t.strip(): out.append((h, t, win_class(h)))
        return True
    u.EnumWindows(WNDENUM(cb), 0); return out


def read_window(h):
    """the window's own caption + the text of every child control (Edit/RichEdit/Static/etc.)"""
    lines = []
    own = win_text(h)
    if own.strip(): lines.append(f"[{win_class(h)}] {own}")
    def cb(ch, lp):
        t = win_text(ch)
        if t.strip(): lines.append(f"  <{win_class(ch)}> {t.strip()[:300]}")
        return True
    u.EnumChildWindows(h, WNDENUM(cb), 0)
    return "\n".join(lines) if lines else "(no readable win32 text - probably a canvas/GPU-drawn app)"


def main():
    a = sys.argv[1:]
    if not a or a[0] == "windows":
        for h, t, c in top_windows():
            print(f"{h:>10}  {c:24.24}  {t[:70]}")
        return
    frag = a[0].lower()
    for h, t, c in top_windows():
        if frag in t.lower():
            print(f"=== reading hwnd={h}  \"{t}\" ===")
            print(read_window(h)); return
    print(f"no visible window matching {a[0]!r}")


if __name__ == "__main__":
    main()
