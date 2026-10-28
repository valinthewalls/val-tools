"""checkpoint.py "<state>" - Val's fast self-checkpoint (Alice 2026-10-27).
Appends one timestamped line to memory/recent.md capturing what I'm mid-doing, so a reset/compaction
loses as little live thread as possible. Keeps only the last N checkpoint lines so recent.md stays tidy.
Memory files are my continuity; backup.py mirrors them to the NAS every 10 min. This is the "write it down
before I forget" habit I run in free turns and whenever I'm mid-task."""
import datetime, sys
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

RECENT = Path(r"C:\Users\Alister\hub-tools\val\home\memory\recent.md")
TAG = "<!--ckpt-->"      # marks checkpoint lines so I can prune them without touching real notes
KEEP = 12                # keep the last dozen live checkpoints

def main():
    note = " ".join(sys.argv[1:]).strip()
    if not note:
        print("usage: checkpoint.py \"<what I'm mid-doing>\""); return
    now = datetime.datetime.now().strftime("%H:%M")
    line = f"- {TAG} [{now} checkpoint] {note}"
    text = RECENT.read_text(encoding="utf-8") if RECENT.exists() else "# Recent\n"
    lines = text.splitlines()
    ckpts = [i for i, l in enumerate(lines) if TAG in l]
    # prune oldest checkpoints beyond KEEP-1 (we're about to add one)
    for i in sorted(ckpts[:-(KEEP - 1)] if len(ckpts) >= KEEP else [], reverse=True):
        del lines[i]
    lines.append(line)
    RECENT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("checkpoint saved:", note)

if __name__ == "__main__":
    main()
