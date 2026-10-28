"""pack_track.py - so I notice when the pack goes quiet (Alice 2026-10-27: "be aware when they haven't replied in a long
time ... react appropriately"). I log every job I hand a bot and where I expect the answer; `check` flags the ones that
are overdue so I follow up, re-task, or hand it to someone else instead of waiting on a reply that may never come back."""
import datetime, json, sys
from pathlib import Path

LOG = Path(r"C:\Users\Alister\hub-tools\val\home\memory\pack_log.json")
OVERDUE_MIN = 45   # if no result after this long, it's gone quiet - react


def load():
    try: return json.loads(LOG.read_text(encoding="utf-8"))
    except Exception: return []


def save(j): LOG.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    a = sys.argv[1:]
    j = load()
    if not a or a[0] == "check":
        now = datetime.datetime.now()
        open_jobs = [x for x in j if x["state"] == "open"]
        if not open_jobs: print("no jobs out to the pack right now."); return
        for x in sorted(open_jobs, key=lambda x: x["sent"]):
            age = (now - datetime.datetime.fromisoformat(x["sent"])).total_seconds() / 60
            tag = "OVERDUE - follow up / re-task" if age > OVERDUE_MIN else f"waiting ({int(age)}m)"
            print(f"#{x['id']} [{tag}] {x['bot']}: {x['task'][:60]}")
            if x.get("expect"): print(f"      check for results: {x['expect']}")
        return
    cmd = a[0]
    if cmd == "sent":
        nid = (max([x["id"] for x in j]) + 1) if j else 1
        rec = {"id": nid, "bot": a[1], "task": a[2], "sent": datetime.datetime.now().isoformat(timespec="seconds"),
               "state": "open", "expect": a[a.index("--expect") + 1] if "--expect" in a else ""}
        j.append(rec); save(j); print(f"logged job #{nid} -> {a[1]}")
    elif cmd == "done":
        x = next((x for x in j if x["id"] == int(a[1])), None)
        if x: x["state"] = "done"; save(j); print(f"job #{a[1]} fulfilled")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
