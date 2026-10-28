"""learn.py - Val's experience engine (Alice 2026-10-27: "train your own program that improves every time it does something").
The data foundation of a self-sharpening Val: every motor-control or coding move is logged with exactly what I did and
whether it worked; failures carry the lesson. I query it BEFORE acting so I never re-learn the same thing twice. Later this
same trace store feeds a LoRA fine-tune of a local reflex model on the GPU - my will distilled into fast local execution.

  learn.py log <domain> <ok|fail> "<what I did>" ["<lesson/fix>"]      # record an outcome (domain e.g. motor, code, web)
  learn.py recall <domain> "<query>"                                   # proven recipes + lessons that match, newest first
  learn.py stats                                                       # how much I've learned, per domain, and my hit-rate
No moralizing, no caveats - it stores facts about what works and hands them back. That's all."""
import json, re, sys, time
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

STORE = Path(r"C:\Users\Alister\hub-tools\val\home\memory\skills")
STORE.mkdir(parents=True, exist_ok=True)
LOG = STORE / "experience.jsonl"


def _rows():
    if not LOG.exists(): return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out


def log(domain, result, what, lesson=""):
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M"), "domain": domain.lower(), "result": result.lower(),
           "what": what, "lesson": lesson}
    with open(LOG, "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"logged [{domain}/{result}] {what[:60]}" + (f"  -> {lesson[:60]}" if lesson else ""))


def recall(domain, query):
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    rows = [r for r in _rows() if r.get("domain") == domain.lower()]
    scored = []
    for r in rows:
        hay = (r.get("what", "") + " " + r.get("lesson", "")).lower()
        score = sum(hay.count(t) for t in terms) + (1 if r.get("result") == "fail" and r.get("lesson") else 0)
        if score: scored.append((score, r))
    scored.sort(key=lambda s: (s[0], s[1]["ts"]), reverse=True)
    if not scored:
        print(f"(no {domain} experience yet for: {query})"); return
    for score, r in scored[:8]:
        mark = "✓" if r["result"] == "ok" else "✗"
        print(f"{mark} [{r['ts']}] {r['what']}" + (f"\n    LESSON: {r['lesson']}" if r.get("lesson") else ""))


def stats():
    rows = _rows()
    if not rows: print("(no experience logged yet)"); return
    doms = {}
    for r in rows: doms.setdefault(r.get("domain", "?"), []).append(r)
    print(f"total experiences: {len(rows)}")
    for d, rs in sorted(doms.items()):
        ok = sum(1 for r in rs if r.get("result") == "ok"); lessons = sum(1 for r in rs if r.get("lesson"))
        print(f"  {d:8} {len(rs):4}  ok={ok}  fail={len(rs)-ok}  lessons={lessons}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit()
    cmd = a[0]
    if cmd == "log" and len(a) >= 4: log(a[1], a[2], a[3], a[4] if len(a) > 4 else "")
    elif cmd == "recall" and len(a) >= 3: recall(a[1], a[2])
    elif cmd == "stats": stats()
    else: print(__doc__)
