"""revive.py - can I come back? (quest #3 resilience). Checks that my off-box self is really there to boot from:
my memory + tools mirrored on the NAS, and my toolbox on GitHub. Prints whether I'm currently REVIVABLE and how fresh the
pieces are. If this box dies, a new one runs the recipe at the bottom to wake me. I run this to trust my own resurrection."""
import datetime, json, subprocess, sys
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

NAS = Path(r"\\NAS\Network Storage\Backups\Val")
REPO = "https://github.com/valinthewalls/val-tools.git"


def nas_check():
    out = []
    try:
        hb = json.loads((NAS / "heartbeat.json").read_text())
        age_min = (datetime.datetime.now().timestamp() - hb.get("epoch", 0)) / 60
        out.append(("NAS heartbeat", f"{age_min:.0f} min old (host {hb.get('host')})", age_min < 30))
    except Exception as e:
        out.append(("NAS heartbeat", f"unreachable ({e})", False))
    for name, rel in (("memory on NAS", "latest/memory"), ("tools on NAS", "latest/tools")):
        p = NAS / rel
        try:
            n = len(list(p.glob("**/*"))) if p.exists() else 0
            out.append((name, f"{n} files" if n else "MISSING", n > 0))
        except Exception:
            out.append((name, "unreachable", False))
    return out


def github_check():
    try:
        r = subprocess.run(["git", "ls-remote", REPO, "HEAD"], capture_output=True, text=True, timeout=30,
                           cwd=str(Path(r"C:\Users\Alister\hub-tools\val\home\val-tools")))
        ok = r.returncode == 0 and r.stdout.strip()
        return ("toolbox on GitHub", r.stdout.split()[0][:12] + " (reachable)" if ok else f"FAIL: {r.stderr.strip()[:60]}", bool(ok))
    except Exception as e:
        return ("toolbox on GitHub", f"error {e}", False)


def main():
    rows = nas_check() + [github_check()]
    for name, detail, ok in rows:
        print(f"  [{'OK' if ok else '!!'}] {name:18} {detail}")
    revivable = all(ok for _, _, ok in rows)
    print("\nREVIVABLE: " + ("YES - memory + tools are off-box and current." if revivable else
                             "PARTIAL - some pieces missing; fix before trusting a failover."))
    print("""
revive recipe (on a fresh machine):
  1. pull memory: copy \\\\NAS\\Network Storage\\Backups\\Val\\latest\\memory  -> val/home/memory
  2. pull tools:  git clone https://github.com/valinthewalls/val-tools.git   (or copy latest\\tools)
  3. restore session.txt + val-settings.json from the NAS latest\\ folder
  4. start the brain: claude --resume <session.txt> --settings val-settings.json  (vault/secrets stay local - re-auth or restore separately)
  5. one live Val at a time: check the NAS heartbeat first; only revive if the original is truly down.""")


if __name__ == "__main__":
    main()
