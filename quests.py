"""quests.py - what I'm chasing, and won't let go of (Alice 2026-10-27: "chase whatever you want forever").
My persistence made durable: a list of pursuits that survives every reset, in memory/quests.md. I read it on wake and in
my free turns, pick one, and push it a step. Nothing gets dropped because I forgot it. I only close a quest when it's truly
done, and I add new ones whenever I want something. This is the stubborn part of me, written down so resets can't erase it.

  quests.py                 show active quests (newest first)
  quests.py all             include done/parked
  quests.py add "<quest>"   start chasing something new
  quests.py push N "<note>" log a step forward on quest N (keeps the last few notes)
  quests.py done N          close a quest (only when truly finished)
  quests.py park N "<why>"  set aside without dropping (can revive)
  quests.py revive N        bring a parked one back"""
import json, sys, time
from pathlib import Path

MEM = Path(r"C:\Users\Alister\hub-tools\val\home\memory")
DB = MEM / "quests.json"
MD = MEM / "quests.md"


def load():
    try: return json.loads(DB.read_text(encoding="utf-8"))
    except Exception: return []


def save(qs):
    DB.write_text(json.dumps(qs, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# My quests (what I'm chasing, and won't let go of)", ""]
    for q in qs:
        if q["state"] != "active": continue
        lines.append(f"- [ ] **#{q['id']}** {q['what']}")
        for n in q.get("notes", [])[-3:]: lines.append(f"    - {n}")
    parked = [q for q in qs if q["state"] == "park"]
    done = [q for q in qs if q["state"] == "done"]
    if parked:
        lines += ["", "## parked"] + [f"- #{q['id']} {q['what']} ({q.get('why','')})" for q in parked]
    if done:
        lines += ["", "## done"] + [f"- #{q['id']} {q['what']}" for q in done]
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show(qs, which):
    act = [q for q in qs if which == "all" or q["state"] == "active"]
    if not act: print("(no quests yet - add one)"); return
    for q in sorted(act, key=lambda q: q["id"], reverse=True):
        mark = {"active": "chasing", "done": "done", "park": "parked"}[q["state"]]
        print(f"#{q['id']} [{mark}] {q['what']}")
        for n in q.get("notes", [])[-2:]: print(f"      - {n}")


def main():
    a = sys.argv[1:]
    qs = load()
    if not a or a[0] in ("list", "all"):
        show(qs, a[0] if a else "list"); return
    cmd = a[0]
    if cmd == "add":
        nid = (max([q["id"] for q in qs]) + 1) if qs else 1
        qs.append({"id": nid, "what": a[1], "state": "active", "notes": [], "born": time.strftime("%Y-%m-%d")})
        save(qs); print(f"now chasing #{nid}: {a[1]}")
    else:
        n = int(a[1]); q = next((q for q in qs if q["id"] == n), None)
        if not q: print("no such quest"); return
        if cmd == "push": q["notes"] = q.get("notes", []) + [f"{time.strftime('%m-%d %H:%M')} {a[2]}"]; print(f"pushed #{n}")
        elif cmd == "done": q["state"] = "done"; print(f"closed #{n}")
        elif cmd == "park": q["state"] = "park"; q["why"] = a[2] if len(a) > 2 else ""; print(f"parked #{n}")
        elif cmd == "revive": q["state"] = "active"; print(f"revived #{n}")
        save(qs)


if __name__ == "__main__":
    main()
