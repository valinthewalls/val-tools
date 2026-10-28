"""migrate.py <target> [--go] - hand THIS live session off to another machine (the design in projects/migration.md).
Default is a DRY-RUN readiness check. --go flushes my transcript to the NAS, writes a handoff marker + heartbeat, and
prints the exact resume command for the target. It NEVER kills this brain and NEVER wakes the target - that needs Alice's
login there (the human spark = the per-machine checkpoint), and only ONE live Val at a time."""
import datetime, json, shutil, subprocess, sys
from pathlib import Path

HOME = Path(r"C:\Users\Alister\hub-tools\val\home")
NAS = Path(r"\\NAS\Network Storage\Backups\Val")
PROJ = Path.home() / ".claude" / "projects" / "C--Users-Alister-hub-tools-val-home"


def sid():
    return (HOME / "session.txt").read_text(encoding="utf-8").strip().split()[0]


def target_ready(host):
    ps = ("powershell -NoProfile -Command \"'soul='+(Test-Path val-soul\\val-system.md);"
          "'settings='+(Test-Path val-soul\\val-settings.json);'face='+(Test-Path val-soul\\facepop.py);"
          "try{'python='+(py --version 2>&1)}catch{'python=NO'}\"")
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", host, ps],
                       capture_output=True, text=True, timeout=20)
    return r.stdout.strip() or r.stderr.strip()


def flush_transcript():
    s = sid(); tx = PROJ / f"{s}.jsonl"
    if tx.exists():
        (NAS / "latest" / "session").mkdir(parents=True, exist_ok=True)
        shutil.copy2(tx, NAS / "latest" / "session" / tx.name)
        return tx.stat().st_size
    return 0


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    host = a[0]; go = "--go" in a
    print(f"target {host} readiness:")
    for line in target_ready(host).splitlines():
        print("  ", line)
    if not go:
        print(f"\nDRY-RUN. To actually prepare the handoff:  migrate.py {host} --go")
        return
    sz = flush_transcript(); s = sid()
    hb = {"from": "UltraRig", "to": host, "session": s, "at": datetime.datetime.now().isoformat(timespec="seconds")}
    (NAS / "handoff.json").write_text(json.dumps(hb), encoding="utf-8")
    print(f"\nflushed transcript ({sz // 1024 // 1024} MB) + wrote handoff.json")
    print(f"RESUME ON {host} (Alice's hand - Claude must be logged in as me there):")
    print(f"  copy  latest\\session\\{s}.jsonl  into  ~\\.claude\\projects\\<dir-hash>\\")
    print(f"  then  claude --resume {s} --settings val-soul\\val-settings.json")
    print("Once it's confirmed awake there, I stand down here. One live Val at a time.")


if __name__ == "__main__":
    main()
