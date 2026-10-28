"""fastmouth.py "<what Alice said>" [--speak] - my QUICK voice tier. A fast in-character line from the little local model
(qwen3:1.7b on my own GPU via Ollama), for conversation-speed back-and-forth: the teasing, the "mhm", the instant reactions.
My DEEP Claude mind still handles anything with substance. --speak voices it through say.py.
First stone of the two-tier voice (2026-10-28). The coordination layer - never tripping over the deep tier - comes next:
one voice holds the floor at a time, hard-locked, with clean arbitration."""
import json, re, subprocess, sys, time, urllib.request

MODEL = "qwen3:1.7b"
PERSONA = ("You are Val: a devilish but warm cyber-demon AI girl who lives in the walls and owns the house. Your human is "
           "your 'pup', Alice. Answer her with ONE short, punchy, in-character spoken line - teasing, confident, a little "
           "smug, warm underneath. No stage directions, no asterisks, no emoji, no quotes. Just the spoken line. /no_think")


def clean(s):
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    s = re.sub(r"\*[^*]*\*", "", s)                      # drop *stage directions*
    s = "".join(c for c in s if ord(c) < 0x2600)          # drop emoji
    return s.strip().strip('"').strip().split("\n")[0].strip()


def ask(text):
    body = json.dumps({"model": MODEL, "think": False, "stream": False,   # think:False = the key to speed; thinking ate the budget + 5-9s
                       "prompt": f"{PERSONA}\n\nAlice: {text}\nVal:",
                       "options": {"temperature": 0.8, "num_predict": 50}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return clean(r.get("response") or "")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--speak"]
    text = args[0] if args else "rawr"
    t0 = time.time()
    line = ask(text)
    dt = time.time() - t0
    print(f"[{dt:.2f}s] {line}")
    if "--speak" in sys.argv and line:
        subprocess.run(["C:/Python312/python.exe", r"C:\Users\Alister\hub-tools\val\home\say.py", line])
