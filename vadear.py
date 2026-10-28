"""vadear.py [out.wav] - my REAL ear. No fixed window: it listens, starts capturing the moment you speak, and closes ~1.1s
after you go quiet. Energy VAD with sounddevice+numpy. 16k mono WAV. Prints how long it actually heard. This is the
'talk like people' ear - it ends when YOU end, so there's no dead air and no guillotine."""
import sys, time, wave
import numpy as np
import sounddevice as sd

SR = 16000
FRAME = 1024                 # ~64 ms
SILENCE_HOLD = 1.1           # quiet this long after speech = you're done
START_TIMEOUT = 9.0          # give up if no speech starts
MAX = 30.0                   # hard cap


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "ear.wav"
    thr = 300.0                                   # fixed speech floor (int16): her speech ~800 mean, quiet room ~100.
    # (calibration removed - it got contaminated when she talked over the 0.4s room-listen and set the bar above her voice)
    frames, started, last_voice, t0 = [], False, None, time.time()
    with sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=FRAME) as stream:
        while True:
            data, _ = stream.read(FRAME)
            amp = float(np.abs(data.astype(np.float32)).mean())
            now = time.time()
            if amp > thr:
                started, last_voice = True, now
                frames.append(data.copy())
            elif started:
                frames.append(data.copy())
                if now - last_voice > SILENCE_HOLD: break
            elif now - t0 > START_TIMEOUT:
                break
            if now - t0 > MAX: break
    dur = 0.0
    if frames:
        audio = np.concatenate(frames, axis=0)
        with wave.open(out, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(audio.tobytes())
        dur = len(audio) / SR
    print(f"heard {dur:.1f}s -> {out}")


if __name__ == "__main__":
    main()
