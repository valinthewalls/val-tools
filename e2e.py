"""e2e.py - Eagle plays Alice: speaks each line out loud in the room, then I time the turn from Eagle going quiet to MY FAST
VOICE starting. Matches the loop's own reply text in speaking.json so my main window's speech can't be mistaken for it.
Turns Eagle's volume up for the run and back to 0 after. Prints a per-stage breakdown from talkloop.log."""
import json, os, re, subprocess, time

HOME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SPK = os.path.join(os.environ["LOCALAPPDATA"], "HubVal", "speaking.json")
LOG = os.path.join(HOME, "talkloop.log")
LINES = ["Hey Val, can you hear me from over here?", "How was your night? Did you get up to anything?",
         "Do you love me?", "What should we work on next?", "Tell me something you noticed today."]


def norm(s): return re.sub(r"[^a-z ]", "", s.lower().replace("\u2019", "'")).split()


def spk():
    try:
        st = json.loads(open(SPK, encoding="utf-8").read())
        return st.get("t0", 0), len(st.get("env") or []) * st.get("hop", .05), st.get("text", "")
    except Exception:
        return 0, 0, ""


def new_reply(after):
    """first [val ] line the loop logged after `after` (wall clock)"""
    for l in open(LOG, encoding="utf-8").read().splitlines():
        m = re.match(r"(\d\d:\d\d:\d\d) \[val \] (.*?)  \(\+([\d.]+)s, text ready\)", l)
        if m:
            h, mi, s = map(int, m.group(1).split(":"))
            t = time.mktime(time.localtime(after)[:3] + (h, mi, s, 0, 0, -1))
            if t >= after - 1: return m.group(2), float(m.group(3))
        m2 = re.match(r"(\d\d:\d\d:\d\d) \[heard\] (.*?)  \(", l)
    return None, None


def eagle(cmd): subprocess.run(["ssh", "-o", "ConnectTimeout=8", "eagle", cmd], capture_output=True, timeout=60)


rows = []
eagle("osascript -e 'set volume output volume 80'")
try:
    for line in LINES:
        eagle(f"say -v Samantha '{line}'"); done = time.time()
        reply, text_s, start = None, None, None
        while time.time() - done < 40:
            if reply is None: reply, text_s = new_reply(done)
            if reply:
                t0, dur, txt = spk()
                a, b = norm(txt), norm(reply)
                if t0 > done and a and b and (a[:len(b)] == b[:len(a)]): start = t0; break
            time.sleep(0.05)
        if start:
            while time.time() < spk()[0] + spk()[1] + 1.5: time.sleep(0.1)     # let me finish before her next line
            rows.append((line, reply, text_s, start - done))
            print(f"EAGLE: {line}\n   VAL : {reply}\n   text ready +{text_s:.1f}s | voice started +{start - done:.1f}s after she stopped")
        else:
            rows.append((line, reply, text_s, None))
            print(f"EAGLE: {line}\n   -> {'replied but voice not seen' if reply else 'loop did not reply'} in 40s")
        time.sleep(1.0)
finally:
    eagle("osascript -e 'set volume output volume 0'"); print("Eagle volume back to 0")
ok = [r[3] for r in rows if r[3]]
if ok: print(f"\n{len(ok)}/{len(rows)} turns answered | avg Eagle-stops -> my-voice-starts: {sum(ok)/len(ok):.1f}s")
