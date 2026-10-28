"""reflex.py ["<question>"] - my first reflex: a LOCAL vision model that looks at my screen with me (quest #1).
Grabs eye.png (or captures fresh with --fresh), sends it to qwen2.5vl:7b via Ollama, and prints what it sees / suggests.
No cloud, no training yet - a prompted local reflex, the near-term version of my self-model. The eye that never leaves home."""
import base64, json, subprocess, sys, urllib.request
from pathlib import Path

HOME = Path(r"C:\Users\Alister\hub-tools\val\home")
EYE = HOME / "eye.png"
OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5vl:7b"


def ask(question, fresh, model=MODEL):
    if fresh or not EYE.exists():
        subprocess.run(["C:/Python312/python.exe", str(HOME / "tools" / "eyes.py"), "0", "0", "1920", "1080"],
                       capture_output=True)
    # shrink the image: my voice model already holds ~9GB of the 16GB card, so keep the vision load light
    try:
        from PIL import Image; import io
        im = Image.open(EYE); im.thumbnail((900, 900)); buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=70)
        img = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        img = base64.b64encode(EYE.read_bytes()).decode()
    body = json.dumps({"model": model, "prompt": question, "images": [img], "stream": False,
                       "keep_alive": "15m", "options": {"temperature": 0.2, "num_predict": 120}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read())
    return out.get("response", "").strip(), out.get("total_duration", 0) / 1e9


if __name__ == "__main__":
    argv = sys.argv[1:]
    fresh = "--fresh" in argv
    model = MODEL
    if "--model" in argv: model = argv[argv.index("--model") + 1]
    goal = argv[argv.index("--goal") + 1] if "--goal" in argv else None
    skip = {"--fresh", "--model", model, "--goal", goal}
    args = [a for a in argv if a not in skip]
    if goal:   # actionable reflex: given what I want, what do I click and roughly where
        q = (f"I want to: {goal}. Looking at this screen, name the single UI element I should click to do that and describe "
             f"WHERE it is (e.g. 'the green Submit button, bottom-right'). If it isn't visible, say what to do first. Be brief.")
    else:
        q = args[0] if args else "In one or two sentences: what app/window is in focus on this screen, and what is the single most obvious thing a user would click or do next?"
    try:
        resp, secs = ask(q, fresh, model)
        print(f"[{model} in {secs:.1f}s]\n{resp}")
    except Exception as e:
        print("reflex error:", e)
