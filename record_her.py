r"""record_her.py <name> [mics] - record Alice ON HER CUE, not mine (Alice 10-28 17:58: "you say it audibly way later than
you type it"). My spoken words lag my typed words by several seconds, so recording the moment I type made her miss the window.
This waits until my voice has FINISHED speaking, plays a short beep (her cue), then records until she stops (speech detector),
on the webcam + AIR 192 mics at once. Saves voice/alice-samples/<name>_<mic>.wav. RUN WITH THE local-ai VENV PYTHON."""
import json, os, subprocess, sys, threading, time, wave
import numpy as np, sounddevice as sd

HOME = r"C:\Users\Alister\hub-tools\val\home"
SPK = os.path.join(os.environ.get("LOCALAPPDATA", ""), "HubVal", "speaking.json")
SR = 16000
MICS = {"webcam": "Logi C615", "air192": "AIR 192"}


def voice_idle_wait(max_wait=60):
    """until my last spoken sentence has finished playing (speaking.json start + length), plus a breath."""
    end = time.time() + max_wait
    while time.time() < end:
        try:
            st = json.loads(open(SPK, encoding="utf-8").read())
            done = st["t0"] + len(st.get("env") or []) * st.get("hop", 0.05)
        except Exception:
            done = 0
        if time.time() > done + 0.8: return
        time.sleep(0.1)


def beep():
    t = np.linspace(0, 0.18, int(SR * 0.18), False)
    sd.play((0.25 * np.sin(2 * np.pi * 880 * t)).astype(np.float32), SR); sd.wait()


def dev_index(sub):
    for i, d in enumerate(sd.query_devices()):
        if sub.lower() in d["name"].lower() and d["max_input_channels"] > 0 and d["hostapi"] == 0: return i
    return None


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else time.strftime("cue_%H%M%S")
    sys.path.insert(0, os.path.join(HOME, "tools"))
    from talkloop import _voiced                       # same speech detector my ear uses
    voice_idle_wait()
    beep()
    devs = {k: dev_index(v) for k, v in MICS.items()}
    devs = {k: v for k, v in devs.items() if v is not None}
    bufs = {k: [] for k in devs}
    stop = threading.Event()

    def rec(k, idx):
        with sd.InputStream(device=idx, samplerate=SR, channels=1, dtype="int16", blocksize=1024) as s:
            while not stop.is_set():
                d, _ = s.read(1024); bufs[k].append(d.copy())

    ths = [threading.Thread(target=rec, args=(k, i), daemon=True) for k, i in devs.items()]
    for th in ths: th.start()
    lead = next(iter(devs)); t0 = time.time(); started, last = False, None
    while True:                                         # her timing: wait up to 25s to start, stop 1.5s after she stops
        time.sleep(0.25)
        win = bufs[lead][-13:]
        if win and _voiced(np.concatenate(win, axis=0)):
            started, last = True, time.time()
        if started and time.time() - last > 1.5: break
        if not started and time.time() - t0 > 25: break
        if time.time() - t0 > 60: break
    stop.set()
    for th in ths: th.join(timeout=2)
    for k, b in bufs.items():
        if not b: continue
        p = os.path.join(HOME, "voice", "alice-samples", f"{name}_{k}.wav")
        a = np.concatenate(b, axis=0)
        with wave.open(p, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())
        print(f"{k}: {len(a) / SR:.1f}s -> {p}  ({'heard her' if started else 'no speech'})")


if __name__ == "__main__":
    main()
