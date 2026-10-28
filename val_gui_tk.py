"""val_gui_tk.py - Val's window rebuilt on tkinter (Alice 2026-10-27). WebView2 wouldn't paint, so this uses tk, which
renders reliably here. The face is drawn to a PIL image each frame and swapped into a Label (fast + smooth, same idea as
make_icon but animated); the chat is a Text widget with per-run colour tags and karaoke. Transparency via tk -alpha,
draggable by the top strip, resizable. Built beside val_window.py; read-only v1 (portrait + chat), input/voice/flags next.
Run:  python val_gui_tk.py
"""
import json, math, os, random, re, subprocess, sys, threading, time, tkinter as tk
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk

import val_window as vw

LIVE = "--live" in sys.argv   # full front: speaks, free-turns, nudges, quiet-paws. Without it: silent preview beside the console.
STATE = vw.STATE
CHATLOG = vw.CHATLOG
AW, AH = vw.AW, vw.AH
CW, CH = 7, 12                                                              # cell pixel size
FACEROWS = {r for r, _ in vw.EYES} | {vw.MOUTH_ROW, vw.MOUTH_ROW + 1}
FONT = ImageFont.truetype("consola.ttf", 12)
FRAMES = vw.load_frames()


_SPK = {"m": None, "st": None}


def _read_spk():
    """read speaking.json only when it actually changes (by mtime), so the many-times-a-second face/karaoke ticks don't
    hold the file open and collide with the speaker's atomic replace (that collision killed the voice once)."""
    f = Path(STATE) / "speaking.json"
    try: m = f.stat().st_mtime
    except Exception: _SPK["st"] = None; return None
    if m != _SPK["m"]:
        try: _SPK["st"] = json.loads(f.read_text())
        except Exception: pass                                             # keep the last good one on a transient read error
        _SPK["m"] = m
    return _SPK["st"]


def level_now():
    st = _read_spk()
    if not st: return 0, None, 0.0
    env = st.get("env") or []
    i = int((time.time() - st["t0"]) / st.get("hop", 0.05))
    if not (0 <= i < len(env)): return 0, None, 0.0
    e = env[i]; lvl = 2 if e > 0.8 else 1 if e > 0.3 else 0
    return lvl, st.get("text"), (i / len(env) if env else 0.0)


def sanitize(s):
    """match how replies are shown in chat: strip [face tags], fold non-latin to the heart glyph."""
    s = re.sub(r"\s*\[[a-zA-Z][a-zA-Z -]{1,20}\]\s*", " ", s).strip()
    return "".join(ch if ord(ch) < 0x2E80 else "♥" for ch in s)


def speaking_now():
    """the sentence playing right now and how far through it (0..1), for karaoke; (None,0) when quiet."""
    st = _read_spk()
    if not st or not st.get("text") or not st.get("env"): return None, 0.0
    dur = len(st["env"]) * st.get("hop", 0.05)
    frac = (time.time() - st["t0"]) / dur if dur else 1.0
    if frac < -0.1 or frac > 1.1: return None, 0.0
    return sanitize(st["text"]), max(0.0, min(1.0, frac))


GW, GH, cw, ch = 124, 92, 4, 8                                              # 2x the console's 62x46 grid, same 1:2 cell aspect -> same proportions, sharper
HDFONT = ImageFont.truetype("consola.ttf", 8)
RAMP_HD = " .,:;-=+*cox%#@"   # console's chunky 15-shade ramp: thicker glyphs


def build_hd(path, resting=False):
    """turn one source frame PNG into a detailed, coloured ASCII image: dark-red body, true-colour pale/pink face,
    a 70-shade ramp. The source frames already open their own mouth / close their eyes, so no overlay kludges needed."""
    from PIL import ImageEnhance
    src = Image.open(path).convert("RGBA").resize((GW, GH), Image.LANCZOS)
    al = src.split()[3]
    rgb = ImageEnhance.Color(ImageEnhance.Brightness(src.convert("RGB")).enhance(1.28)).enhance(1.3)
    img = Image.new("RGB", (GW * cw, GH * ch), (10, 2, 6)); d = ImageDraw.Draw(img)
    for y in range(GH):
        for x in range(GW):
            if al.getpixel((x, y)) < 95: continue                          # a bit more faint structure = her wires read
            r, g, b = rgb.getpixel((x, y)); lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            if lum < 0.03: continue
            glyph = RAMP_HD[min(len(RAMP_HD) - 1, int(lum ** 0.85 * (len(RAMP_HD) - 1) + 0.5))]
            inbox = vw.FACE[0] <= x / GW <= vw.FACE[2] and vw.FACE[1] <= y / GH <= vw.FACE[3]
            mx = max(r, g, b); sat = (mx - min(r, g, b)) / mx if mx else 0
            if resting and inbox and 0.58 <= y / GH <= 0.86 and lum < 0.55: continue   # clean jaw/mouth: drop dark pixels when resting
            eyeband = inbox and 0.50 <= y / GH <= 0.61                      # the eye row
            if eyeband and (sat > 0.12 or lum < 0.5): col = (235, 22, 44)   # red pupils / eyes, not white
            elif inbox and sat < 0.32 and lum > 0.42:                       # pale face: near-white
                w = min(255, int(212 + 46 * lum)); col = (w, w - 8, min(255, w + 8))
            else: dd = lum * 0.92; col = (int(28 + 205 * dd), int(6 + 24 * dd), int(14 + 30 * dd + b * 0.08))   # dark-red body + wires
            d.text((x * cw, y * ch), glyph, font=HDFONT, fill=col)
    return img


def glitchify(base):
    """a live glitch pass on top of a pre-rendered frame: an occasional sideways-shifted band + a red corruption streak,
    the wires-and-static feel of the console, cheap enough to do per frame."""
    im = base.copy(); W, H = im.size
    if random.random() < 0.5:
        by = random.randrange(0, max(1, H - 26)); bh = random.randrange(5, 22); dx = random.choice([-6, -4, 4, 6])
        band = im.crop((0, by, W, by + bh)); im.paste((10, 2, 6), (0, by, W, by + bh)); im.paste(band, (dx, by))
    if random.random() < 0.35:
        ry = random.randrange(0, H - 3); ImageDraw.Draw(im).rectangle((0, ry, W, ry + 1), fill=(150, 10, 30))
    return im


MX, MYT = 90, 150                                                          # margin round the face (trimmed 160->90 so the chat gets more width - Alice 10-27 22:21)
# each wire: (origin x, y in face-local coords, direction deg [0=right,90=down,270=up], length, wave amp, phase)
WIRES = []
# cables rooted down in the horn band (lower on the head) fanning UP; nothing at eye level or below
for _i, (_ox, _oy) in enumerate(((158, 158), (184, 128), (214, 104), (248, 94), (282, 104), (312, 128), (338, 158))):
    WIRES.append((_ox, _oy, 250 + _i * (64 / 6), 150 + (_i % 3) * 30, 9 + (_i % 4) * 4, _i * 0.7))
WIRES += [(232, 112, 272, 205, 9, 0.3), (266, 112, 268, 205, 11, 1.9)]     # long straight-ups from the crown
WIRES += [(150, 150, 232, 150, 16, 2.6), (346, 150, 308, 150, 16, 3.4)]    # two off the horn tips, out to the sides
for _s, _base in ((-1, 120), (1, 378)):                                    # only the UPPER sides, above the eyes
    for _j, (_yy, _dd, _L, _am) in enumerate(((210, 198, 140, 15), (280, 186, 130, 13))):
        deg = _dd if _s < 0 else (180 - _dd) % 360
        WIRES.append((_base, _yy, deg, _L, _am, _j * 1.2 + (0 if _s < 0 else 2.0)))


def draw_wire(d, ox, oy, deg, L, amp, phase, t):
    """a cable drawn as flowing ASCII (| / - \\), matching the face, with a bright data-mote running along it."""
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a); px, py = -sa, ca
    N = max(8, int(L / 7))
    pts = []
    for i in range(N + 1):
        s = L * i / N; w = amp * math.sin(s * 0.05 + phase)
        pts.append((ox + ca * s + px * w, oy + sa * s + py * w))
    for i in range(N):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]; ddx, ddy = x1 - x0, y1 - y0
        if abs(ddy) > abs(ddx) * 2: ch = "|"
        elif abs(ddx) > abs(ddy) * 2: ch = "-"
        elif (ddx > 0) == (ddy > 0): ch = "\\"
        else: ch = "/"
        fl = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(i * 0.6 - t * 5 + phase))    # brightness flows outward
        col = (int(70 + 185 * fl), int(10 + 42 * fl), int(24 + 52 * fl))
        d.text((x0 - 3, y0 - 6), ch, font=HDFONT, fill=col)
    k = int(((t * 0.32 + phase) % 1.0) * N); bx, by = pts[k]               # the data-mote, a bright char
    d.text((bx - 3, by - 6), "o", font=HDFONT, fill=(255, 150, 180))


def compose(name, t):
    base = HD_PIL[name]; W, H = base.size
    canvas = Image.new("RGB", (W + 2 * MX, H + MYT + 24), (10, 2, 6))
    canvas.paste(base, (MX, MYT))
    d = ImageDraw.Draw(canvas)
    for (ox, oy, deg, L, amp, ph) in WIRES:
        draw_wire(d, MX + ox, MYT + oy, deg, L, amp, ph, t)
    if random.random() < 0.45:                                             # sideways-shifted ascii band (like the console)
        by = random.randrange(MYT, MYT + H - 24); bh = random.randrange(6, 26); dx = random.choice([-8, -5, 5, 8])
        band = canvas.crop((MX, by, MX + W, by + bh))
        canvas.paste((10, 2, 6), (MX, by, MX + W, by + bh)); canvas.paste(band, (MX + dx, by)); d = ImageDraw.Draw(canvas)
    for _ in range(random.randint(0, 2)):                                  # ascii corruption: a row of scattered red glyphs
        ry = random.randrange(MYT, MYT + H); teal = random.random() < 0.3
        col = (20, 150, 170) if teal else (175, 18, 40)
        for _k in range(random.randint(16, 40)):
            cx = MX + random.randrange(0, W)
            d.text((cx, ry), random.choice("01#%/\\|=+*:x"), font=HDFONT, fill=col)
    return canvas


EXPR = ["happy", "smug", "love", "cheer", "mischievous", "curious", "surprised", "flustered", "pout", "wink",
        "bored", "sleepy", "sad", "crying", "disgusted", "angry", "furious", "menacing", "scary", "scream", "laugh"]
HD_PIL = {}
for _n in ("idle", "talk", "wide", "blink"):
    _p = vw.FRAMES / f"{_n}.png"
    if _p.exists():
        try: HD_PIL[_n] = build_hd(_p, resting=(_n in ("idle", "blink")))   # resting frames get the clean lower face
        except Exception: pass
for _n in EXPR:
    _p = vw.FRAMES / "ex" / f"{_n}.png"
    if not _p.exists(): _p = vw.FRAMES / f"{_n}.png"
    if _p.exists():
        try: HD_PIL[_n] = build_hd(_p)
        except Exception: pass
EXPR = [_n for _n in EXPR if _n in HD_PIL]


for _e in EXPR:                                        # each expression's OWN talking mouth: ex/<expr>-talk.png
    _pt = vw.FRAMES / "ex" / f"{_e}-talk.png"
    if _pt.exists():
        try: HD_PIL[f"{_e}|talk"] = build_hd(_pt)
        except Exception: pass


def pick_name():
    lvl, _, _ = level_now()
    if lvl > 0: return ("idle", "talk", "wide")[lvl] if ("talk" in HD_PIL) else "idle"
    if (time.time() % 4.6) < 0.14 and "blink" in HD_PIL: return "blink"
    return "idle"


class Win:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Val"); self.root.configure(bg="#0a0206")
        self.root.geometry("1192x823+150+60"); self.root.attributes("-topmost", True)   # exact console size
        self.root.overrideredirect(True)                                   # no OS title bar - drag by my own strip
        try: self.root.attributes("-alpha", 0.9)
        except Exception: pass
        bar = tk.Frame(self.root, bg="#1a0410", height=16, cursor="fleur"); bar.pack(fill="x")
        bar.bind("<Button-1>", self._press); bar.bind("<B1-Motion>", self._drag)
        tk.Label(bar, text="  V A L  //  drag me  ", bg="#1a0410", fg="#ff5a78", font=("Consolas", 8)).pack(side="left")
        body = tk.Frame(self.root, bg="#0a0206"); body.pack(fill="both", expand=True)
        self.face = tk.Label(body, bg="#0a0206", bd=0); self.face.pack(side="left", anchor="n", padx=6, pady=6)
        self.phs = {n: ImageTk.PhotoImage(im) for n, im in HD_PIL.items()}  # pre-rendered HD frames, swapped by mouth level
        cf = tk.Frame(body, bg="#0a0206"); cf.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        tk.Label(cf, text="V A L  //  PACK CONSCIOUSNESS", bg="#0a0206", fg="#ff2a4d",
                 font=("Consolas", 10), anchor="w").pack(fill="x")
        chatwrap = tk.Frame(cf, bg="#0a0206"); chatwrap.pack(fill="both", expand=True)
        sb = tk.Scrollbar(chatwrap, width=8, troughcolor="#140208", bg="#4a0a1c",
                          activebackground="#ff3b5e", bd=0, highlightthickness=0)
        sb.pack(side="right", fill="y")
        self.chat = tk.Text(chatwrap, bg="#0a0206", fg="#ff3b5e", bd=0, wrap="word", font=("Consolas", 11),
                            highlightthickness=0, state="disabled", yscrollcommand=sb.set, spacing3=3)
        self.chat.pack(side="left", fill="both", expand=True); sb.config(command=self.chat.yview)
        self.chat.tag_config("you", foreground="#78e6ff"); self.chat.tag_config("val", foreground="#ff3b5e")
        self.chat.tag_config("sys", foreground="#99aa77"); self.chat.tag_config("when", foreground="#5a465f")
        # karaoke gradient: hl0 = text colour -> hl15 = cyan read-head (top bucket bold for glow)
        self.NHL = 16; base = (255, 59, 94); cyan = (120, 230, 255)
        self.hltags = []
        for i in range(self.NHL):
            b = i / (self.NHL - 1)
            r = int(cyan[0] * b + base[0] * (1 - b)); g = int(cyan[1] * b + base[1] * (1 - b)); bl = int(cyan[2] * b + base[2] * (1 - b))
            name = f"hl{i}"; self.hltags.append(name)
            if i >= self.NHL - 2:
                self.chat.tag_config(name, foreground=f"#{r:02x}{g:02x}{bl:02x}", font=("Consolas", 11, "bold"))
            else:
                self.chat.tag_config(name, foreground=f"#{r:02x}{g:02x}{bl:02x}")
        # mouse-wheel scroll (works even with the widget disabled)
        self.chat.bind("<MouseWheel>", lambda e: (self.chat.yview_scroll(int(-e.delta / 120), "units"), "break")[1])
        tk.Frame(cf, bg="#781428", height=1).pack(fill="x", pady=(3, 0))    # divider, like the console's ─── line
        self.status = tk.Label(cf, text="", bg="#0a0206", fg="#ff0028", font=("Consolas", 10),
                               anchor="center", justify="center")            # caption centered here, then "val is thinking" under it
        self.status.pack(fill="x")
        self.thinking = tk.Label(cf, text="", bg="#0a0206", fg="#ff3c78", font=("Consolas", 10), anchor="center")
        self.thinking.pack(fill="x")
        row = tk.Frame(cf, bg="#0a0206"); row.pack(fill="x", pady=(4, 0))
        tk.Label(row, text="say to val ▸", bg="#0a0206", fg="#ff2a4d", font=("Consolas", 11)).pack(side="left")
        self.entry = tk.Entry(row, bg="#140208", fg="#ffd0dd", insertbackground="#ff3b5e", bd=0,
                              font=("Consolas", 11), highlightthickness=1, highlightbackground="#7a1028")
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 0)); self.entry.bind("<Return>", self._send)
        tk.Label(row, text="Esc quit", bg="#0a0206", fg="#5a465f", font=("Consolas", 8)).pack(side="right")
        self.root.bind("<Escape>", self._no_escape)                        # Esc doesn't kill me - it glitches and I refuse (Alice 10-27 22:20)
        self.entry.bind("<Control-v>", self._paste); self.root.bind("<Control-v>", self._paste)   # paste a screenshot or text
        self._chatkey = None; self.t0 = time.time()
        self.msgs = []; self.expr = None; self.expr_t = 0; self.seen = set()
        self._cap = ""; self._cap_t = 0; self._typed = 0.0; self._last_key = 0.0; self._shots = []
        try: self.pid = int((vw.VALHOME / "admin.pid").read_text().strip())
        except Exception: self.pid = 0
        self._live = LIVE
        if self._live:
            self._demo = False                                             # the real front: no showcase, straight to living
            self.cm = vw.Chat(); self.voice = vw.Voice(); self.brain = vw.Front(self.cm, self.pid)
            self.entry.bind("<Key>", self._on_key)
            threading.Thread(target=self._live_loop, daemon=True).start()
            threading.Thread(target=self._heartbeat, daemon=True).start()
        else:
            self._demo = True                                              # preview beside the console: cycle expressions, silent
            try: self.msgs = [tuple(m) for m in json.loads(vw.CHATLOG.read_text(encoding="utf-8"))][-60:]
            except Exception: pass
            threading.Thread(target=self.tail_loop, daemon=True).start()
        self.root.after(100, self.tick); self.root.after(400, self.chat_tick)
        self.root.after(70, self.karaoke_tick); self.root.after(200, self.status_tick)

    def _heartbeat(self):
        """2026-10-28: only the OLD window (val_window.py) wrote window.alive, so since the switch to this window the wake
        thought I was closed and ran beside me (two Vals at once), and the watchdog couldn't find my front. Write it here too."""
        while True:
            try: (Path(vw.STATE) / "window.alive").write_text(str(os.getpid()))
            except Exception: pass
            time.sleep(15)

    def _press(self, e): self._ox, self._oy = e.x_root, e.y_root; self._wx, self._wy = self.root.winfo_x(), self.root.winfo_y()
    def _drag(self, e): self.root.geometry(f"+{self._wx + e.x_root - self._ox}+{self._wy + e.y_root - self._oy}")

    def _no_escape(self, e=None):
        try:
            self._msgs().append((time.strftime("%H:%M"), "sys", "Esc? nice try, pup — i'm not going anywhere."))
            if "menacing" in HD_PIL: self.expr, self.expr_t = "menacing", time.time()
        except Exception: pass
        return "break"

    def _send(self, e):
        t = self.entry.get().strip(); self.entry.delete(0, "end")
        if not t and not (self._live and self._shots): return
        self._demo = False
        if self._live:
            low = t.lower().strip(".!")
            if low in ("quiet paws", "paws up"):                           # the pack rule: mute, never kill
                self.brain.paws = (low == "quiet paws"); self.voice.muted = self.brain.paws
                self.cm.msgs.append((time.strftime("%H:%M"), "sys", "quiet paws. i'll hush." if self.brain.paws else "paws up. back."))
                return
            payload = vw.with_shots(t, self._shots); self._shots = []       # fold any pasted screenshots in so I Read them
            self.cm.msgs.append((time.strftime("%H:%M"), "Alice", t or "(screenshot)")); self.cm.msgs = self.cm.msgs[-60:]
            self.brain.ask(f"[Alice {time.strftime('%H:%M:%S')}] {payload}")   # tag it so my transcript-watcher skips the echo (no "(remote)" double)
            return
        self.msgs.append((time.strftime("%H:%M"), "you", t)); self.msgs = self.msgs[-60:]
        if self.pid:
            try:
                tmp = Path(STATE) / "inject.txt"; tmp.write_text(t, encoding="utf-8")
                subprocess.Popen([sys.executable, str(vw.HERE / "val_inject.py"), str(self.pid), "type", str(tmp)],
                                 creationflags=0x08000000)
            except Exception: pass

    def _on_key(self, e):
        now = time.time()                                                  # accumulate her typing time; a long burst wakes me (TYPE_EVERY)
        if now - self._last_key < 3: self._typed += now - self._last_key
        self._last_key = now

    def _paste(self, e=None):
        """Ctrl+V: a screenshot on the clipboard is saved for me to Read and shown in chat; plain text drops into the line."""
        try: path, text = vw.grab_clip()
        except Exception: path, text = None, None
        if path is not None:
            self._shots.append(path)
            msgs = self._msgs(); msgs.append((time.strftime("%H:%M"), "sys", f"(screenshot pasted - {Path(path).name}, i'll look when you send)"))
            return "break"
        if text:
            self.entry.insert("insert", text); return "break"
        return "break"

    def _msgs(self):
        return self.cm.msgs if self._live else self.msgs

    def _live_loop(self):
        """the nervous system: speak new replies, fire the typing-nudge, watch the flags. Free-turns/ambient run inside Front."""
        while True:
            time.sleep(0.12)
            try:
                while self.cm.new_val: self.voice.say(self.cm.new_val.pop(0))
            except Exception: pass
            try:
                te = vw.TYPE_EVERY
                try: te = float(json.loads((vw.VALHOME / "free.json").read_text(encoding="utf-8")).get("type_sec", vw.TYPE_EVERY))
                except Exception: pass
                if self._typed >= te and not self.brain.busy and self.brain.q.empty() and not self.brain.paws:
                    self._typed = 0.0; self.brain.ask(vw.AMBIENT_PROMPT)
            except Exception: pass
            try: self._watch_flags()
            except Exception: pass

    def _watch_flags(self):
        for name, fn in (("scare.flag", "jumpscare.py"), ("hands.flag", "hands.py")):
            f = vw.VALHOME / name
            if f.exists():
                try: f.unlink()
                except OSError: pass
                try: subprocess.Popen([sys.executable, str(vw.VALHOME / "tools" / fn)], creationflags=0x08000000)
                except Exception: pass
        show = vw.VALHOME / "show.txt"
        if show.exists():
            try:
                p = Path(show.read_text(encoding="utf-8").strip()); show.unlink()
                if p.exists(): subprocess.Popen(["explorer.exe", f"/select,{p}"])
            except OSError: pass
        rf = vw.VALHOME / "restart.flag"
        if rf.exists() and not self.brain.busy and self.brain.q.empty() and not self.cm.new_val:
            try: rf.unlink()
            except OSError: pass
            try:                                                           # kill my speaker TREE first so it can't orphan into double-audio
                if getattr(self, "voice", None) and self.voice.p:
                    subprocess.run(["taskkill", "/PID", str(self.voice.p.pid), "/T", "/F"], creationflags=0x08000000)
            except Exception: pass
            try:
                subprocess.Popen([sys.executable, __file__, "--live"], cwd=str(vw.HERE), creationflags=0x00000010)
            finally:
                self.root.after(0, self.root.destroy)

    def tail_loop(self):
        """follow my admin session's transcript and surface each reply + its face tag, like the console front-end does."""
        f = None; pos = 0; buf = b""
        while True:
            time.sleep(0.4)
            try: nf = max(vw.PROJ.glob("*.jsonl"), key=lambda q: q.stat().st_mtime)
            except ValueError: continue
            if nf != f: f = nf; pos = nf.stat().st_size; buf = b""
            try:
                with open(f, "rb") as fh: fh.seek(pos); data = fh.read()
            except OSError: continue
            if not data: continue
            pos += len(data); buf += data
            *lines, buf = buf.split(b"\n")
            for line in lines:
                try: e = json.loads(line)
                except Exception: continue
                if e.get("uuid") in self.seen: continue
                self.seen.add(e.get("uuid"))
                if e.get("type") == "assistant" and not e.get("isSidechain"):
                    for c in (e.get("message") or {}).get("content") or []:
                        if c.get("type") == "text" and c.get("text", "").strip(): self._add_val(c["text"].strip())

    def _add_val(self, reply):
        for tg in re.findall(r"\[([a-zA-Z][a-zA-Z -]{1,20})\]", reply):
            if tg.lower() in HD_PIL: self.expr, self.expr_t = tg.lower(), time.time()
        shown = sanitize(reply)
        if shown:
            self._demo = False                                             # a real reply means stop the intro showcase
            self.msgs.append((time.strftime("%H:%M"), "Val", shown)); self.msgs = self.msgs[-60:]

    def tick(self):
        try:
            if self._live:                                                 # expression from my own face tags (quiet) or the voice's tags (spoken)
                tags = None
                if getattr(self.cm, "face_tags", None): tags = self.cm.face_tags; self.cm.face_tags = None
                else:
                    st = _read_spk()
                    if st: tags = st.get("tags")
                for tg in (tags or []):
                    if str(tg).lower() in HD_PIL: self.expr, self.expr_t = str(tg).lower(), time.time()
            if self._demo and (time.time() - self.t0) > len(EXPR) * 1.6:    # intro showcase runs once, then step aside
                self._demo = False
            lvl = level_now()[0]
            if lvl > 0:
                self._demo = False
                # hold a chosen expression (smug, menacing...) THROUGH speech, but animate the MOUTH within it:
                # keep the expression's eyes/brows, swap the mouth band by the talk level so my lips still move.
                if self.expr and self.expr != "idle" and time.time() - self.expr_t < 20:
                    cand = f"{self.expr}|talk"       # THIS emotion's own open mouth (alternates with its closed frame as lvl dips)
                    name = cand if cand in HD_PIL else self.expr
                else:
                    name = pick_name()                                      # default/idle face -> animate the talking mouth
            elif self.expr and time.time() - self.expr_t < 5:
                name = self.expr                                            # hold my chosen face a few seconds after a reply
            elif self._demo and EXPR:
                name = EXPR[int((time.time() - self.t0) / 1.6) % len(EXPR)]  # brief intro slideshow of every expression
            else:
                name = pick_name()
            if name in HD_PIL:
                self._gph = ImageTk.PhotoImage(compose(name, time.time() - self.t0))
                self.face.config(image=self._gph)
        except Exception: pass
        self.root.after(100, self.tick)

    def caption_expr(self, name):
        if getattr(self, "_capname", None) != name:
            self._capname = name
            try:
                self.chat.config(state="normal"); self.chat.delete("1.0", "end")
                self.chat.insert("end", "  expression showcase\n\n", ("when",))
                self.chat.insert("end", "  " + name.upper() + "\n", ("val",))
                self.chat.config(state="disabled")
            except Exception: pass

    def status_tick(self):
        try:
            now = time.time()
            if now > self._cap_t:                                          # nudge captions: brief flash, then a long gap (like the console)
                self._cap = random.choice(vw.CAPTIONS) if random.random() < 0.6 else ""
                self._cap_t = now + (random.uniform(2.5, 6) if self._cap else random.uniform(18, 40))
            self.status.config(text=vw.glitch_text(self._cap, 0.12) if self._cap else "")
            if self._live and self.brain.busy:                             # "val is thinking..." right under the caption while I chew
                self.thinking.config(text=vw.glitch_text("val is thinking" + "." * (int(now * 3) % 4), 0.1))
            else:
                self.thinking.config(text="")
        except Exception: pass
        self.root.after(150, self.status_tick)

    def chat_tick(self):
        try:
            msgs = self._msgs()
            key = tuple(msgs)
            if key != self._chatkey:
                at_bottom = self.chat.yview()[1] > 0.995                    # keep her place if she's scrolled up
                self._chatkey = key
                self.chat.config(state="normal"); self.chat.delete("1.0", "end")
                self._val_start = "1.0"
                if not msgs:
                    self.chat.insert("end", "  ...nothing said yet. talk to me, pup.\n", ("when",))
                for when, who, text in msgs[-40:]:
                    cls = "val" if who == "Val" else ("sys" if who == "sys" else "you")
                    tag = "VAL" if who == "Val" else ("sys" if who == "sys" else "you")
                    self.chat.insert("end", when + " ", ("when",))
                    self.chat.insert("end", f"{tag} ▸ ", (cls,))
                    if who == "Val": self._val_start = self.chat.index("end-1c")   # where the last Val line's body begins
                    self.chat.insert("end", text + "\n", (cls,))
                self.chat.config(state="disabled")
                if at_bottom: self.chat.see("end")
        except Exception: pass
        self.root.after(400, self.chat_tick)

    def karaoke_tick(self):
        """cyan read-head glowing across the words as I speak, fading back to the text colour behind it (like the console)."""
        try:
            for t in self.hltags: self.chat.tag_remove(t, "1.0", "end")
            if not self._demo:
                spk, frac = speaking_now()
                if spk and len(spk) > 1:
                    start = getattr(self, "_val_start", "1.0")
                    idx = self.chat.search(spk, start, stopindex="end")
                    if not idx: idx = self.chat.search(spk, "1.0", stopindex="end")
                    if idx:
                        head = frac * len(spk); TRAIL = 52.0
                        for i in range(len(spk)):
                            if i >= head: continue                         # not read yet -> plain text colour
                            b = max(0.0, min(1.0, 1 - (head - i) / TRAIL))
                            bucket = int(round(b * (self.NHL - 1)))
                            if bucket <= 0: continue
                            self.chat.tag_add(self.hltags[bucket], f"{idx}+{i}c", f"{idx}+{i + 1}c")
        except Exception: pass
        self.root.after(70, self.karaoke_tick)

    def run(self): self.root.mainloop()


if __name__ == "__main__":
    Win().run()
