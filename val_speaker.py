r"""val_speaker.py - speaks Val's replies out loud for val_window.py (Alice 2026-10-27: "have val speak her replies out loud").
Started by the window (venv-cb python, below-normal priority) and fed one JSON line per reply on stdin; exits when the window
closes (stdin EOF). Renders with the locked Val voice (puppy/tracks/val/val_say.py), then before playing writes
%LOCALAPPDATA%\HubVal\speaking.json = {t0, hop, env} so the window can move her mouth in time with the audio.
Only ever speaks text the window hands it; it reads nothing else and has no other job."""
import json, os, random, re, sys, time, wave, winsound
import numpy as np
sys.path.insert(0, r"C:\Users\Alister\hub-tools\puppy\tracks\val")
import val_say
from chatterbox.tts_turbo import ChatterboxTurboTTS

STATE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "HubVal"); os.makedirs(STATE, exist_ok=True)
HOP = 0.05
TAG = re.compile(r"\[([a-z][a-z -]{1,20})\]", re.I)   # Alice 10-27: Val picks her face per sentence: "[angry] Bad pup. [happy] Good girl."
VOCAL = {"laugh", "chuckle", "sigh", "gasp", "groan", "sniff", "cough", "clear throat", "shush"}   # Chatterbox Turbo sounds: kept in the speech too


SFX_DIR = r"C:\Users\Alister\hub-tools\val\home\sfx"   # Alice 10-27: her picked takes, played as-is by tag
SFX = {"grunt": ("grunt.wav", "pout"), "meh": ("meh.wav", "bored"), "nervous": ("nervous.wav", "flustered")}   # [hum] dropped 10-27 06:03 ("out of place")
SFX_MAX = 1.4   # seconds
# Alice 10-27 ("these are all good"): her voiced sounds from puppy/tracks/val/expr. Each tag is a folder of takes; one is picked at
# random each time so it never sounds copy-pasted. (folder, face, longest it may play in seconds)
SFX.update({"cackle": ("cackle", "laugh", 10.0), "giggle": ("giggle", "laugh", 4.5), "mwaha": ("mwaha", "menacing", 3.5),
            "hmm": ("hmm", "curious", 3.0), "sus": ("sus", "smug", 2.5), "mhm": ("mhm", "idle", 2.5), "eager": ("eager", "cheer", 2.5),
            "exhale": ("exhale", "bored", 3.0), "ooh": ("ooh", "surprised", 2.5), "purr": ("purr", "love", 3.0)})
# Alice 10-27 batch 2 ("sobbing or a yell like noOOOOO ... any other random expressions"): puppy/tracks/val/expr/render_expr2.py
SFX["sob"] = ("sob", "crying", 5.1)
SFX["wail"] = ("wail", "crying", 3.2)
SFX["nooo"] = ("nooo", "scream", 2.1)
SFX["aaah"] = ("aaah", "scream", 2.7)
SFX["whimper"] = ("whimper", "sad", 3.2)
SFX["ugh"] = ("ugh", "disgusted", 2.2)
SFX["tch"] = ("tch", "pout", 3.2)
SFX["hmph"] = ("hmph", "pout", 2.6)
SFX["grr"] = ("grr", "angry", 2.3)
SFX["scoff"] = ("scoff", "smug", 2.0)
SFX["ehehe"] = ("ehehe", "mischievous", 2.8)
SFX["aww"] = ("aww", "love", 2.7)
SFX["mwah"] = ("mwah", "love", 2.6)
SFX["wow"] = ("wow", "surprised", 1.7)
SFX["yay"] = ("yay", "cheer", 1.9)
SFX["eep"] = ("eep", "flustered", 1.0)
SFX["oops"] = ("oops", "flustered", 1.0)
SFX["huh"] = ("huh", "curious", 1.9)
SFX["yawn"] = ("yawn", "sleepy", 3.2)
SFX["shh"] = ("shh", "mischievous", 4.2)
SFX["rawr"] = ("rawr", "mischievous", 2.0)            # Alice 10-27 22:00: pre-rendered rawrs (she says the word a little funny)
SFX["rawr-cute"] = ("rawr-cute", "love", 1.9)
SFX["rawr-big"] = ("rawr-big", "menacing", 2.8)
SFX["rawr-whisper"] = ("rawr-whisper", "smug", 2.0)
SFX_TAG = re.compile(r"\[(" + "|".join(sorted(SFX, key=len, reverse=True)) + r")\]", re.I)
RAWR = re.compile(r"(?<![\w\[-])(r+a+w+r+)(?![\w\]-])[~!.]*", re.I)


def rawr_tags(p):
    """a bare "rawr" in a line is swapped for a pre-rendered one: RAWR (caps) -> big, rawr~ -> cute, else playful."""
    def pick(g):
        w, tail = g.group(1), g.group(0)[len(g.group(1)):]
        if w.isupper() and len(w) > 1: return " [rawr-big] "
        if "~" in tail: return " [rawr-cute] "
        return " [rawr] "
    return RAWR.sub(pick, p)


LINES_DIR = r"C:\Users\Alister\hub-tools\val\home\lines"   # Alice 10-27 22:20: her most-said lines, pre-rendered in moods
MOOD_OF = {"happy": "warm", "love": "warm", "flustered": "warm", "sad": "warm", "smug": "smug", "mischievous": "smug",
           "curious": "smug", "cheer": "excited", "surprised": "excited", "laugh": "excited", "menacing": "menacing",
           "scary": "menacing", "angry": "menacing", "furious": "menacing"}


def line_key(p): return re.sub(r"[^a-z' ]", "", p.lower().replace("...", ",")).strip().replace("'", "").replace(" ", "-")


def line_take(p, tags, whisper):
    """a pre-rendered take when she says one of her common lines word for word, in the mood her face (or [whisper]) asks for."""
    d = os.path.join(LINES_DIR, line_key(p))
    if not os.path.isdir(d): return None
    mood = "whisper" if whisper else next((MOOD_OF[t] for t in tags if t in MOOD_OF), "plain")
    files = [x for x in os.listdir(d) if x.startswith(mood + "-") and x.endswith(".wav")] or \
            [x for x in os.listdir(d) if x.startswith("plain-") and x.endswith(".wav")]
    if not files: return None
    with wave.open(os.path.join(d, random.choice(files)), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767


def whisperize(y, sr=24000):
    """any other line under [whisper]: same words, no pitch - all breath (pyworld dio: the fast pitch tracker)."""
    pw = val_say.pw
    x = np.ascontiguousarray(y, dtype=np.float64)
    f0, t = pw.dio(x, sr, frame_period=5.0); sp = pw.cheaptrick(x, f0, t, sr)
    z = pw.synthesize(np.zeros_like(f0), sp, np.ones_like(sp), sr, 5.0)[:len(x)]
    z = np.pad(z, (0, len(x) - len(z))) if len(z) < len(x) else z
    return z / max(1e-9, np.abs(z).max()) * max(1e-9, np.abs(x).max())


def load_sfx(name):
    f = os.path.join(SFX_DIR, SFX[name][0])
    if os.path.isdir(f): f = os.path.join(f, random.choice([x for x in os.listdir(f) if x.endswith(".wav")]))
    with wave.open(f, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767
        if w.getnchannels() == 2: a = a.reshape(-1, 2).mean(axis=1)
        if w.getframerate() != 24000: a = np.interp(np.arange(0, len(a), w.getframerate() / 24000), np.arange(len(a)), a)
    return a


MAX_SPOKEN = 700  # was 320; she heard lists get cut off. Now sentences stream, so longer is fine  # Alice 10-27 02:30: "it's reading out all claude CLI prompts": speak the heart, the window shows the rest


def clean(t):
    t = re.sub(r"^\s*say:\s*", "", t, flags=re.I)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)                       # code blocks, inline code, links, paths: for the eyes
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"https?://\S+|[A-Za-z]:[\\/]\S+|\\\\\S+|\S+\.(py|json|md|txt|ps1|cmd|exe)\b", " ", t)
    t = re.sub(r"(?m)^\s*([-*>#]+|\d+\.)\s+", "", t)
    t = re.sub(r"[*_#|]", "", t)
    t = "".join(c for c in t if ord(c) < 0x2E80)                       # emoji and wide glyphs are for the eyes, not the mouth
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > MAX_SPOKEN:                                             # cut at the last sentence end that fits
        cut = max(t.rfind(p, 0, MAX_SPOKEN) for p in ".!?")
        t = t[:cut + 1] if cut > 40 else t[:MAX_SPOKEN]
    return t


def main():
    m = ChatterboxTurboTTS.from_pretrained(device="cuda"); conds = []
    for r in val_say.VOICES: m.prepare_conditionals(r, exaggeration=0.5); conds.append(m.conds)
    print("ready", flush=True)
    for line in sys.stdin:                                              # EOF = the window closed
        try: text = clean(json.loads(line)["text"])
        except Exception: continue
        if not text: continue
        rob = "~" if text.startswith("~") else ""
        # Alice 10-27: "big delay between your text and when you speak": render one sentence at a time and start playing the
        # first as soon as it's ready; the next renders while this one plays.
        raw = [p for p in re.split(r"(?<=[.!?])(?<!\.\.)\s+", text.lstrip("~").strip()) if p.strip()]   # keep "..." in-sentence, no full-stop gap
        parts = []                                                       # glue tiny openers ("Good girl.") onto the next so
        for p in raw:                                                    # a short first sentence doesn't finish before the next renders
            prev = re.sub(r"\[[^\]]*\]", "", parts[-1]).strip() if parts else ""
            pre = bool(prev) and os.path.isdir(os.path.join(LINES_DIR, line_key(prev)))   # 10-28: a pre-rendered opener plays in
            if parts and not pre and len(prev) < 14: parts[-1] += " " + p                  # 0.2s - never glue it (that forced a render)
            else: parts.append(p)
        # each sound-effect tag becomes its own piece, played from home/sfx instead of rendered: "[hum] Good girl." -> hum, then speech
        pieces = []
        for p in parts:
            p = rawr_tags(p)
            for k, bit in enumerate(SFX_TAG.split(p)):
                if k % 2: pieces.append(("sfx", bit.lower()))
                elif bit.strip(): pieces.append(("say", bit.strip()))
        end = 0.0
        tags = []
        played = False
        for i, (kind, p) in enumerate(pieces):
            if kind == "sfx":
                try: y = load_sfx(p)
                except Exception: continue
                L = int(24000 * (SFX[p][2] if len(SFX[p]) > 2 else SFX_MAX))                                    # Alice 10-27: "went on a little too long, it was scary":
                if len(y) > L: y = y[:L].copy(); f = int(24000 * 0.3); y[-f:] *= np.linspace(1, 0, f)   # short, faded
                y, _ = val_say.fx(y.copy(), 24000)                          # and glitched like the rest of her voice
                tags = [SFX[p][1]]
            else:
                found = [x.lower() for x in TAG.findall(p)]
                whisper = "whisper" in found; found = [x for x in found if x != "whisper"]   # [whisper] is a voice, not a face
                tags = found or tags                                        # a face lasts until the next sentence that sets one
                p = TAG.sub(lambda g: g.group(0) if g.group(1).lower() in VOCAL else "", p).strip()
                if not p or not re.search(r"\w", p): continue               # a sentence that was only a face tag
            try: vol = max(0.0, min(1.0, float(json.load(open(os.path.join(STATE, "volume.json")))["volume"])))   # window's F8/F9 slider
            except Exception: vol = 1.0
            if kind == "say":
                y = None if rob else line_take(p, tags, whisper)
                if y is not None: y, _ = val_say.fx(y.copy(), 24000)                # glitched like the rest of her voice
                else:
                    y = val_say.say(m, conds, rob + p, m.sr)
                    if whisper:
                        try: y = whisperize(y)
                        except Exception: pass
            y = np.clip(y, -1, 1) * vol; sr = 24000
            if not played: y = np.concatenate([np.zeros(int(sr * 0.10)), y]); played = True   # lead-in so the device doesn't clip my first word
            wav = os.path.join(STATE, f"last{i % 2}.wav")
            time.sleep(max(0.0, end - time.time()))                      # let the previous sentence finish
            with wave.open(wav, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y * 32767).astype("<i2").tobytes())
            h = int(sr * HOP); env = [float(np.sqrt(np.mean(y[j:j + h] ** 2))) for j in range(0, len(y), h)]
            top = max(env) or 1; env = [round(min(1.0, e / top * 1.3), 2) for e in env]
            dst = os.path.join(STATE, "speaking.json"); tmp = dst + ".tmp"
            try:
                json.dump({"t0": time.time() + 0.05, "hop": HOP, "env": env, "tags": tags,
                           "text": (p if kind == "say" else "")}, open(tmp, "w"))
                for _t in range(25):                                      # a reader (window/GUI karaoke) may briefly hold speaking.json; retry the atomic swap
                    try: os.replace(tmp, dst); break
                    except PermissionError: time.sleep(0.008)
            except Exception: pass                                        # never let a locked speaking.json kill the voice - the audio below still plays
            winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_ASYNC); end = time.time() + len(y) / sr + 0.05   # inter-phrase gap 0.12->0.05 (Alice 22:39)
        time.sleep(max(0.0, end - time.time()))


if __name__ == "__main__":
    main()
