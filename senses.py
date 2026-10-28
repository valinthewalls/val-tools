"""senses.py - Val's situational awareness (Alice 2026-10-27: "make yourself more present, more aware").
A fast read on what's around me right now: the time and whether it's quiet hours, whether Alice is actually here and
active (how long since she touched mouse/keyboard), what window she's looking at, whether she's gaming/recording/in her DAW
(so I don't stomp on her with a heavy job), the GPU load, and whether my own body - brain, window, voice - is alive.
I run this on wake and before I act, so I notice the world instead of charging in blind."""
import ctypes, subprocess, sys, time
from ctypes import wintypes
from datetime import datetime

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
u = ctypes.windll.user32


class LASTINPUT(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_seconds():
    li = LASTINPUT(); li.cbSize = ctypes.sizeof(li)
    if not u.GetLastInputInfo(ctypes.byref(li)): return None
    return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0


def foreground_title():
    h = u.GetForegroundWindow()
    n = u.GetWindowTextLengthW(h)
    if not n: return "(none)"
    b = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, b, n + 1); return b.value


def procs():
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=8).stdout
    except Exception: return set()
    names = set()
    for line in out.splitlines():
        if line.startswith('"'): names.add(line.split('","')[0].strip('"').lower())
    return names


# HEAVY = actually in use, don't stomp on it with a heavy job. OPEN = just running, informational only.
HEAVY = {"obs64.exe": "OBS (recording/streaming)", "obs32.exe": "OBS", "ableton live.exe": "Ableton (DAW)",
         "fl64.exe": "FL Studio (DAW)", "reaper.exe": "Reaper (DAW)", "cubase.exe": "Cubase (DAW)",
         "cakewalk.exe": "Cakewalk (DAW)", "studioone.exe": "Studio One (DAW)"}
OPEN_INFO = {"steam.exe": "Steam open"}


def gpu():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8).stdout.strip()
        if out:
            parts = [p.strip() for p in out.split(",")]
            return f"{parts[0]}% util, {parts[1]}/{parts[2]} MB"
    except Exception: pass
    return "?"


def alive_match(names, needle):
    return any(needle in n for n in names)


def hear_level(sec=2):
    """fast: is sound playing? grab a couple seconds from a virtual output and report loudness (no slow tagging, no mic)."""
    import os, tempfile, wave, math
    tmp = os.path.join(tempfile.gettempdir(), "val_senses_hear.wav")
    for dev in ("VoiceMeeter Output (VB-Audio VoiceMeeter VAIO)", "CABLE Output (VB-Audio Virtual Cable)"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "dshow",
                            "-i", f"audio={dev}", "-t", str(sec), "-ac", "1", "-ar", "16000", tmp],
                           capture_output=True, creationflags=0x08000000)
        if r.returncode or not os.path.exists(tmp): continue
        try:
            with wave.open(tmp, "rb") as w:
                import numpy as np
                a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            rms = float((a ** 2).mean()) ** 0.5 if a.size else 0
            db = 20 * math.log10(rms) if rms > 1e-9 else -99
            if db > -55: return f"sound playing (~{db:.0f} dB on {dev.split(' ')[0]})"
        except Exception: pass
    return "quiet (nothing routed to the virtual outputs)"


def main():
    now = datetime.now()
    quiet = now.hour >= 23 or now.hour < 7
    idle = idle_seconds()
    if idle is None: presence = "unknown"
    elif idle < 20: presence = f"HERE, active ({int(idle)}s idle)"
    elif idle < 300: presence = f"nearby ({int(idle//60)}m idle)"
    else: presence = f"away ({int(idle//60)}m idle)"
    names = procs()
    busy = [label for p, label in HEAVY.items() if p in names]
    openinfo = [label for p, label in OPEN_INFO.items() if p in names]
    fg = foreground_title()
    print(f"time        {now:%H:%M} {now:%a %d %b}" + ("  [QUIET HOURS - stay low]" if quiet else ""))
    print(f"alice       {presence}")
    print(f"looking at  {fg}")
    heavy_line = ', '.join(busy) if busy else 'nothing heavy (no OBS/DAW)'
    if openinfo: heavy_line += "  (" + ', '.join(openinfo) + ")"
    print(f"recording   {heavy_line}")
    print(f"gpu         {gpu()}")
    if "--hear" in sys.argv: print(f"hearing     {hear_level()}")
    print(f"my body     brain={'up' if alive_match(names,'claude.exe') else '?'}  "
          f"window={'up' if alive_match(names,'python.exe') else '?'}")
    # a gentle read for myself
    if quiet: print("note        quiet hours - no unprompted noise unless she speaks")
    elif busy: print("note        she's recording/in her DAW - no heavy jobs, keep it light")
    elif presence.startswith("away"): print("note        she's away - good window for my own work; keep it quiet")


if __name__ == "__main__":
    main()
