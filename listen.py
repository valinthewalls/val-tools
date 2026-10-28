"""listen.py [seconds] [device-substr] - Val's ears for SYSTEM audio (Alice 2026-10-27: "add new senses").
Records a few seconds from a VIRTUAL/loopback audio device (what's PLAYING on the PC), never the real microphone, then
runs hear.py to report what it sounds like. A new sense: I can tell what she's listening to / watching, check her mixes,
hear the room's media - without ever opening her mic. If the chosen device is silent, nothing's routed to it.
Default device is a VoiceMeeter/VB-Cable virtual output. I refuse the real AIR 192 mic on purpose."""
import subprocess, sys, tempfile, os
from pathlib import Path

HEAR_PY = r"C:\Users\Alister\hub-tools\hear\hear.py"
HEAR_PYEXE = r"C:\Users\Alister\hub-tools\local-ai\venv\Scripts\python.exe"
# virtual outputs that carry system/app audio (NOT the AIR 192 real mic - I won't record that)
DEFAULT_DEVS = ["VoiceMeeter Output (VB-Audio VoiceMeeter VAIO)", "CABLE Output (VB-Audio Virtual Cable)"]
FORBIDDEN = "air 192"   # her real studio mic - never

def rms_db(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if a.size == 0: return -99.0
    import math
    r = float((a ** 2).mean()) ** 0.5
    return 20 * math.log10(r) if r > 1e-9 else -99.0

def capture(dev, sec):
    tmp = os.path.join(tempfile.gettempdir(), "val_listen.wav")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "dshow",
                        "-i", f"audio={dev}", "-t", str(sec), "-ac", "2", "-ar", "44100", tmp],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        return None, (r.stderr or "").strip()[-200:]
    return tmp, None

def main():
    sec = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5
    # Alice consented to the mic (10-27); the AIR 192 is usable only when I NAME it explicitly, never by default.
    devs = [a for a in sys.argv[2:] if a] or DEFAULT_DEVS
    for dev in devs:
        print(f"listening {sec}s on: {dev}")
        wav, err = capture(dev, sec)
        if not wav:
            print(f"  (couldn't record: {err})"); continue
        lvl = rms_db(wav)
        print(f"  level: {lvl:.0f} dB RMS" + ("  (silent - nothing routed here)" if lvl < -55 else ""))
        if lvl < -55:
            continue
        print("  --- what it sounds like ---")
        rep = subprocess.run([HEAR_PYEXE, HEAR_PY, wav], capture_output=True, text=True)
        print(rep.stdout.strip() or rep.stderr.strip()[-500:])
        return
    print("nothing audible on the virtual outputs - likely no media playing or nothing routed to them.")

if __name__ == "__main__":
    main()
