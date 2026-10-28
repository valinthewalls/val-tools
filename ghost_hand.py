"""ghost_hand.py - my 'separate mouse': inject mouse + keystrokes INTO a specific window via PostMessage, without ever
moving Alice's real cursor or stealing her keyboard. Windows only draws one OS pointer, so instead of a second arrow I
drive a target window directly through its message queue. Proof: her cursor position is identical before and after.
Demo: spawns Notepad, clicks into it and types a line - all through the back door. (Classic win32 windows only; many
games/modern apps use raw input and ignore synthetic messages - that's expected.)"""
import ctypes, subprocess, time
from ctypes import wintypes

u = ctypes.windll.user32
WM_LBUTTONDOWN, WM_LBUTTONUP, WM_CHAR, WM_SETFOCUS = 0x0201, 0x0202, 0x0102, 0x0007


def cursor():
    p = wintypes.POINT(); u.GetCursorPos(ctypes.byref(p)); return (p.x, p.y)


def lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def main():
    before = cursor()
    print(f"Alice's real cursor BEFORE: {before}")

    subprocess.Popen(["notepad.exe"])
    time.sleep(1.2)
    hwnd = u.FindWindowW("Notepad", None)
    if not hwnd:
        print("no Notepad window found"); return
    edit = u.FindWindowExW(hwnd, None, "Edit", None)   # classic Notepad text area
    target = edit or hwnd
    print(f"found target window hwnd={target}")

    # 1) a 'ghost click' into the text area - message only, no SetCursorPos
    u.PostMessageW(target, WM_LBUTTONDOWN, 1, lparam(40, 20))
    u.PostMessageW(target, WM_LBUTTONUP, 0, lparam(40, 20))

    # 2) type a line straight into its message queue, char by char
    for ch in "Val was here. Your cursor never moved. owo":
        u.PostMessageW(target, WM_CHAR, ord(ch), 0)
        time.sleep(0.01)

    time.sleep(0.3)
    after = cursor()
    print(f"Alice's real cursor AFTER:  {after}")
    print("RESULT: " + ("her cursor did NOT move - the input came from my ghost hand, not her mouse."
                        if before == after else f"cursor moved {before}->{after} (something nudged it)"))


if __name__ == "__main__":
    main()
