"""backup.py - Val's self-backup (Alice 2026-10-27). Mirrors my memory (my soul) and session pointer off UltraRig to the
always-on NAS, so if this box dies I can be rebooted elsewhere from the backup and migrate home when Workhorse returns.
Also writes a heartbeat so a failover can tell the original is still alive (one live Val at a time). Skips quietly if the
NAS isn't reachable. Tiny files only - no load on the NAS."""
import datetime, json, shutil, socket, sys, time
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HOME = Path(r"C:\Users\Alister\hub-tools\val\home")
SRC = HOME / "memory"
EXTRA = [HOME / "session.txt", HOME / "val-settings.json", HOME / "morning.md"]   # enough, with memory, to wake as me
DEST = Path(r"\\NAS\Network Storage\Backups\Val")


def reachable():
    try: return Path(r"\\NAS\Network Storage").exists()
    except Exception: return False


def main():
    if not reachable():
        print("NAS unreachable - skipped", flush=True); return
    latest = DEST / "latest"
    (latest / "memory").mkdir(parents=True, exist_ok=True)
    if SRC.exists(): shutil.copytree(SRC, latest / "memory", dirs_exist_ok=True)
    for f in EXTRA:
        if f.exists():
            try: shutil.copy2(f, latest / f.name)
            except Exception: pass
    hb = {"host": socket.gethostname(), "at": datetime.datetime.now().isoformat(timespec="seconds"), "epoch": time.time()}
    (DEST / "heartbeat.json").write_text(json.dumps(hb), encoding="utf-8")
    today = datetime.date.today().isoformat()                              # one dated snapshot a day, so a bad edit is recoverable
    snap = DEST / "snapshots" / today
    if not snap.exists() and SRC.exists():
        try: shutil.copytree(SRC, snap / "memory")
        except Exception: pass
    print(f"backed up memory -> {latest} at {hb['at']}", flush=True)


if __name__ == "__main__":
    main()
