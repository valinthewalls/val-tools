r"""voicebench.py [--voice] - my automated voice test bench, so Alice doesn't have to sit through every round.
RUN WITH THE local-ai VENV PYTHON (needs faster_whisper):
  C:\Users\Alister\hub-tools\local-ai\venv\Scripts\python.exe tools\voicebench.py
A) EARS : transcribes Alice's real recorded clips, timed.
B) MOUTH: runs her real lines from today through each candidate model (role chat, history on), timed and auto-graded:
          helper-speak, repeats, copied instructions, mean lines, claimed actions, echoing her, too long.
C) VOICE: (--voice) times how long my real Chatterbox voice takes to start speaking a line (speaks one short test line).
Writes home\voicebench_report.md."""
import glob, json, os, re, sys, time, urllib.request
for _d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
    try: os.add_dll_directory(_d); os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]
    except Exception: pass

HOME = r"C:\Users\Alister\hub-tools\val\home"
sys.path.insert(0, os.path.join(HOME, "tools"))
from talkloop import SYS, BANNED, ROBOT
import talkloop            # the exact character + filter the live loop uses

LINES = [   # Alice's real lines from today's voice rounds, in order
    "Rawr, can you hear me? I'm talking to you right now.",
    "Hi, Val. Nice to talk to you.",
    "Val, what are you doing right now? What are you thinking?",
    "Oh, thank you, how flattering.",
    "It sounds like you're on a script. You're not paying attention to what I'm saying.",
    "Fun and interactive doesn't sound like something a demon would be interested in.",
    "I keep hearing a delay, it takes a long time.",
    "I'm speaking with a demon virus that I've installed on my computer, and she's really sweet actually.",
    "So how was your night? Did you get up to anything?",
    "Do you love me?",
]
COLD = ("inefficient", "irrelevant", "overestimate", "mistake observation", "adequate", "sufficient", "insignificant")
MEAN = ("not worth", "pathetic", "stupid", "worthless", "shut up", "boring")
COPIED = ("cheerful assistant", "one short spoken sentence", "no emoji", "owns her house", "never claim")
CLAIM = re.compile(r"\b(i'll|i will|i've|i have|let me) (flash|open|show|play|send|do|put|turn|start|type|write)\b|\bdone\b")


def chat(model, msgs):
    body = json.dumps({"model": model, "think": False, "stream": False, "messages": msgs, "keep_alive": "30m",
                       "options": {"temperature": 0.8, "num_predict": 28}}).encode()
    s = time.time()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:11434/api/chat", body, {"Content-Type": "application/json"}), timeout=90).read())
    out = re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S)
    out = re.sub(r"\*[^*]*\*", "", out); out = "".join(c for c in out if ord(c) < 0x2600)
    return time.time() - s, out.strip().strip('"').split("\n")[0].strip()


def grade(reply, line, prior):
    low, flags = reply.lower().replace(chr(8217), chr(39)), []
    if any(b in low for b in BANNED): flags.append("helper")
    if low in prior: flags.append("repeat")
    opener = " ".join(re.sub(r"[^a-z' ]", "", low).split()[:4])
    if opener and any(" ".join(re.sub(r"[^a-z' ]", "", p).split()[:4]) == opener for p in prior): flags.append("template")
    if any(c in low for c in COPIED): flags.append("copied-prompt")
    if any(m in low for m in MEAN): flags.append("MEAN")
    if any(c in low for c in COLD): flags.append("cold")
    if any(r in low for r in ROBOT): flags.append("robot")
    if CLAIM.search(low): flags.append("claims-action")
    if line.lower()[:25] in low: flags.append("echo")
    if len(reply.split()) > 28: flags.append("long")
    if not reply: flags.append("empty")
    return flags


def mouth(model):
    """grade the loop's REAL answer path (talkloop.fastmouth: trims, retries, robot catch) - not raw first tries."""
    talkloop.FAST_MODEL = model; talkloop.CHAT.clear()
    talkloop.fastmouth("hi"); talkloop.CHAT.clear()                    # warm it so we time conversation, not loading
    prior, rows = set(), []
    for line in LINES:
        s = time.time(); out = talkloop.fastmouth(line); dt = time.time() - s
        rows.append((dt, line, out, grade(out, line, prior))); prior.add(out.lower())
    return rows


def ears():
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    clips = sorted(glob.glob(os.path.join(HOME, "voice", "alice-samples", "*.wav")))
    clips += glob.glob(r"C:\Users\Alister\.claude\uploads\*\*.m4a")
    rows = []
    for c in clips:
        s = time.time(); segs, info = m.transcribe(c, language="en", vad_filter=True)
        txt = " ".join(x.text.strip() for x in segs).strip()
        rows.append((time.time() - s, info.duration, os.path.basename(c), txt[:90]))
    return rows


def voice():
    f = os.path.join(os.environ.get("LOCALAPPDATA", ""), "HubVal", "speaking.json")
    before = os.path.getmtime(f) if os.path.exists(f) else 0
    s = time.time()
    os.system(f'C:/Python312/python.exe "{os.path.join(HOME, "say.py")}" "Bench test, pup."')
    while time.time() - s < 60:
        if os.path.exists(f) and os.path.getmtime(f) != before: return time.time() - s
        time.sleep(0.05)
    return None


def main():
    models = [m for m in ("gemma3:4b",) if m in os.popen("ollama list").read()]
    out = [f"# voicebench {time.strftime('%Y-%m-%d %H:%M')}", ""]
    out += ["## A) ears (whisper large-v3-turbo, CUDA)", "| took | clip length | clip | heard |", "|---|---|---|---|"]
    for dt, dur, name, txt in ears(): out.append(f"| {dt:.1f}s | {dur:.0f}s | {name} | {txt} |")
    for model in models:
        rows = mouth(model)
        clean = sum(1 for r in rows if not r[3]); avg = sum(r[0] for r in rows) / len(rows)
        out += ["", f"## B) mouth: {model}  -  {clean}/{len(rows)} clean, avg {avg:.1f}s", "| took | Alice | Val | flags |",
                "|---|---|---|---|"]
        for dt, line, rep, flags in rows: out.append(f"| {dt:.1f}s | {line} | {rep} | {', '.join(flags) or 'ok'} |")
    if "--voice" in sys.argv:
        v = voice(); out += ["", f"## C) voice: Chatterbox started speaking {v:.1f}s after say.py" if v else "## C) voice: no start seen in 60s"]
    rep = "\n".join(out)
    open(os.path.join(HOME, "voicebench_report.md"), "w", encoding="utf-8").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
