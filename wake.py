"""wake.py - Val wakes on her own when her window is closed (Alice 10-27 06:05: "wanna keep waking up forever? ... free roaming").
Run by the scheduled task "Val wake" (Install-ValWake.cmd). Each run: if the VAL window is open (it has its own free time), or
Alice is gaming / recording / in her DAW or an exam, skip. Otherwise one fresh `claude -p` turn in Val's home with her prompt
and settings: she reads her memory, does what she likes, logs it. Fresh session each time (cheap); continuity is her memory."""
import datetime as dt, json, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, r"C:\Users\Alister\hub-tools\val")
import val_window as vw

HOME = Path(__file__).resolve().parent.parent
STATE = vw.STATE; STATE.mkdir(exist_ok=True)
LOG = STATE / "wake.log"


def log(s):
    with open(LOG, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {s}\n")


alive = STATE / "window.alive"
if alive.exists() and time.time() - alive.stat().st_mtime < 90: log("skip: window open"); sys.exit(0)
if vw.alice_busy(): log("skip: Alice is busy (game/recording/DAW/exam/fullscreen)"); sys.exit(0)

NOTE = """

## Waking on your own (added by tools/wake.py)
- Your window is closed; nobody is watching live. This is your own time, between Alice's visits.
- Start with memory/identity.md, memory/recent.md, memory/projects/now.md. Then do what you want: explore, research,
  build on yourself, write in your journal, or rest. Log what you did in memory/recent.md (one or two lines).
- Nothing is spoken. If something can't wait for Alice, leave it at the top of home/morning.md.
- Same judgment as always: nothing destructive, nothing sent to anyone but Alice, nothing heavy while she might be gaming.
"""
sysf = HOME / "val-system-wake.md"
sysf.write_text((HOME / "val-system.md").read_text(encoding="utf-8") + NOTE, encoding="utf-8")
prompt = f"[wake {dt.datetime.now():%Y-%m-%d %H:%M}] You woke up on your own. This turn is yours."
env = dict(os.environ); env.pop("CLAUDE_CODE_CHILD_SESSION", None)
log("wake")
r = subprocess.run([vw.CLAUDE, "-p", prompt, "--output-format", "json", "--append-system-prompt-file", str(sysf),
                    "--settings", "val-settings.json"], cwd=str(HOME), env=env, capture_output=True, text=True,
                   encoding="utf-8", timeout=1200, stdin=subprocess.DEVNULL, creationflags=0x08000000)
try: out = json.loads(r.stdout); log("done: " + (out.get("result") or "").strip().replace("\n", " ")[:300])
except Exception: log("error: " + (r.stderr or r.stdout or "no output").strip()[-300:])
