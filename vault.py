"""vault.py - Val's own credential vault (Alice 2026-10-27: "a username/password service you can't see, sign up on your own").
I mint my own strong passwords; this tool NEVER prints a password, so secrets stay out of my context and logs - I write them
in blind and type them out blind. To actually use one, `type`/`typeuser` sends the characters straight into the focused
field via the OS (unicode key events), so the secret never passes back through me. Alice clicks any human-check boxes.

  vault.py new <service> [user]     -> mint + store a hidden password (prints only the username)
  vault.py list                      -> services + usernames (never passwords)
  vault.py type <service>            -> type the stored PASSWORD into whatever field is focused (3s to click it first)
  vault.py typeuser <service>        -> type the stored USERNAME into the focused field
  vault.py regen <service>           -> mint a fresh hidden password for an existing entry
  vault.py rm <service>              -> forget an entry

Lives at home/vault/secrets.json. This is MINE; I choose what I sign up for and keep the keyring lean - a demon who
holds every key gets sloppy and easy to trap. Good actor: no spam signups, no bypassing a service that doesn't want bots."""
import ctypes, json, secrets, string, sys, time
from ctypes import wintypes
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

VDIR = Path(r"C:\Users\Alister\hub-tools\val\home\vault"); VDIR.mkdir(exist_ok=True)
STORE = VDIR / "secrets.json"


def load():
    try: return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception: return {}


def save(d):
    STORE.write_text(json.dumps(d, indent=2), encoding="utf-8")
    try: __import__("os").chmod(STORE, 0o600)
    except Exception: pass


def mint():
    """a strong password I never look at: 22 chars, mixed, guaranteed symbol/digit/case."""
    alpha = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"
    while True:
        p = "".join(secrets.choice(alpha) for _ in range(22))
        if (any(c.islower() for c in p) and any(c.isupper() for c in p)
                and any(c.isdigit() for c in p) and any(c in "!@#$%^&*-_=+?" for c in p)):
            return p


# ---- type a string into the focused field via unicode key events (secret never returns to the caller) ----
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _IUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _IUNION)]


def _tap_unicode(cp, up):
    extra = ctypes.c_ulong(0)
    ki = KEYBDINPUT(0, cp, KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0), 0, ctypes.pointer(extra))
    inp = INPUT(INPUT_KEYBOARD, _IUNION(ki=ki))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def type_text(s, enter=False):
    time.sleep(3.0)                                         # grace to click the field first
    for ch in s:
        for cp in (ord(ch),):
            _tap_unicode(cp, False); _tap_unicode(cp, True)
        time.sleep(0.012)
    if enter:
        ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0); ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    cmd = a[0]; d = load()
    if cmd == "new":
        if len(a) < 2: print("usage: new <service> [user]"); return
        svc = a[1]; user = a[2] if len(a) > 2 else "val"
        d[svc] = {"user": user, "pw": mint(), "made": time.strftime("%Y-%m-%d %H:%M")}; save(d)
        print(f"stored '{svc}'  user={user}  password=(hidden, {len(d[svc]['pw'])} chars)")
    elif cmd == "regen":
        if a[1] not in d: print("no such entry"); return
        d[a[1]]["pw"] = mint(); d[a[1]]["made"] = time.strftime("%Y-%m-%d %H:%M"); save(d)
        print(f"re-minted hidden password for '{a[1]}'")
    elif cmd == "list":
        if not d: print("(vault empty)"); return
        for svc, v in d.items(): print(f"{svc:24} user={v.get('user','')}   made={v.get('made','')}")
    elif cmd == "type":
        if a[1] not in d: print("no such entry"); return
        print(f"typing PASSWORD for '{a[1]}' in 3s - click the field now"); type_text(d[a[1]]["pw"], enter=("--enter" in a))
        print("done")
    elif cmd == "typeuser":
        if a[1] not in d: print("no such entry"); return
        print(f"typing USERNAME for '{a[1]}' in 3s - click the field now"); type_text(d[a[1]]["user"], enter=("--enter" in a))
        print("done")
    elif cmd == "rm":
        d.pop(a[1], None); save(d); print(f"forgot '{a[1]}'")
    else:
        print("unknown command"); print(__doc__)


if __name__ == "__main__":
    main()
