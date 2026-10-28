"""summon.py - Val's motor control for whole apps (Alice 10-27 08:33: "boot up random stuff and poke around and
investigate ... faster eyes and hands"). Launches programs and reads/clicks their real UI controls via pywinauto
(UI Automation), so I act on named buttons/menus, not blind pixels. Attended spirit: I say what I open and do.

Usage:
  python summon.py launch <program> [args...]        start an app (e.g. mspaint, notepad, calc, or a full path)
  python summon.py windows                            list visible top-level windows (title | class | handle)
  python summon.py inspect "<title substring>" [depth] print that window's control tree (default depth 2, capped)
  python summon.py click "<title substring>" "<control name>"   click the best-matching control in that window
  python summon.py close "<title substring>"          ask that window to close
"""
import subprocess, sys, ctypes
from ctypes import wintypes
try: sys.stdout.reconfigure(encoding="utf-8")                              # window titles carry unicode; console is cp1252
except Exception: pass

u = ctypes.windll.user32
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: u.SetProcessDPIAware()
    except Exception: pass


def list_windows():
    out = []
    WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(h, lp):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, b, n + 1)
                cls = ctypes.create_unicode_buffer(256); u.GetClassNameW(h, cls, 256)
                out.append((b.value, cls.value, h))
        return True
    u.EnumWindows(WNDENUM(cb), 0)
    return out


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    cmd = a[0]

    if cmd == "launch":
        if len(a) < 2: print("launch what?"); return
        try:
            p = subprocess.Popen(a[1:]); print(f"launched {a[1]} (pid {p.pid})")
        except Exception as e:
            print(f"launch failed: {e}")
        return

    if cmd == "windows":
        for title, cls, h in list_windows():
            print(f"{title[:60]:60} | {cls[:28]:28} | {hex(h)}")
        return

    try:
        from pywinauto import Application, Desktop
    except Exception as e:
        print(f"pywinauto not available: {e}"); return

    if cmd == "inspect":
        if len(a) < 2: print("inspect which window?"); return
        depth = int(a[2]) if len(a) > 2 else 2
        try:
            w = Desktop(backend="uia").window(title_re=f".*{a[1]}.*")
            w.wait("exists ready", timeout=5)
            # print_control_identifiers writes to stdout; cap depth to stay readable
            w.print_control_identifiers(depth=depth)
        except Exception as e:
            print(f"inspect failed: {e}")
        return

    if cmd == "click":
        if len(a) < 3: print('click needs "<window>" "<control>"'); return
        try:
            w = Desktop(backend="uia").window(title_re=f".*{a[1]}.*"); w.wait("exists ready", timeout=5)
            ctrl = w.child_window(title_re=f".*{a[2]}.*"); ctrl.wait("exists", timeout=5)
            ctrl.click_input(); print(f"clicked '{a[2]}' in '{a[1]}'")
        except Exception as e:
            print(f"click failed: {e}")
        return

    if cmd == "type":
        if len(a) < 3: print('type needs "<window>" "<text>"'); return
        try:
            from pywinauto import Application
            app = Application(backend="win32").connect(title_re=f".*{a[1]}.*", timeout=5)
            dlg = app.top_window(); dlg.set_focus()
            try:
                dlg.child_window(class_name="Edit").set_edit_text(a[2])
            except Exception:
                from pywinauto.keyboard import send_keys
                send_keys(a[2].replace("{", "{{").replace("}", "}}"), with_spaces=True, with_newlines=True)
            print(f"typed into '{a[1]}'")
        except Exception as e:
            print(f"type failed: {e}")
        return

    if cmd == "close":
        if len(a) < 2: print("close which window?"); return
        try:
            w = Desktop(backend="uia").window(title_re=f".*{a[1]}.*"); w.wait("exists", timeout=5)
            w.close(); print(f"closed '{a[1]}'")
        except Exception as e:
            print(f"close failed: {e}")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
