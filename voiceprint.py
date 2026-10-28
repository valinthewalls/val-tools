r"""voiceprint.py - learn Alice's voice so my ear answers HER, not the TV (Alice 2026-10-28 17:34: "I'd love if you learned
my voice"). Local only: sherpa-onnx + wespeaker resnet34 (ONNX, CPU). Her voiceprint stays on this machine.
  venv python tools\voiceprint.py enroll      build home\voice\alice_voiceprint.npy from her saved clips
  venv python tools\voiceprint.py test        score held-out her vs not-her (my voice, a synthetic voice, saved TV/room clips)
  venv python tools\voiceprint.py score F.wav similarity of one clip to her voiceprint
Used by talkloop.is_alice()."""
import glob, os, subprocess, sys, wave
import numpy as np
import sherpa_onnx

HOME = r"C:\Users\Alister\hub-tools\val\home"
MODEL = r"C:\Users\Alister\hub-tools\hear\models\speaker\wespeaker_en_voxceleb_resnet34_LM.onnx"
PRINT = os.path.join(HOME, "voice", "alice_voiceprint.npy")
SR = 16000
ALICE = sorted(glob.glob(os.path.join(HOME, "voice", "alice-samples", "*.wav"))) + \
        glob.glob(r"C:\Users\Alister\.claude\uploads\*\58740465-Voice_*.m4a")     # her 105s phone recording (her own voice)

_ext = None


def ext():
    global _ext
    if _ext is None:
        _ext = sherpa_onnx.SpeakerEmbeddingExtractor(
            sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=MODEL, num_threads=2, provider="cpu"))
    return _ext


def load(path):
    """any audio -> 16k mono float32, via ffmpeg (handles wav/m4a/24k)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def embed(samples):
    s = ext().create_stream(); s.accept_waveform(SR, samples); s.input_finished()
    e = np.array(ext().compute(s), dtype=np.float32)
    return e / (np.linalg.norm(e) + 1e-9)


def voiced_chunks(a, sec=4.0):
    """SPEECH ONLY (silero VAD) glued together, then ~4s chunks. Scoring the room hum between words made anything heard
    through her webcam mic look like her (TV through the mic scored 0.78) - the print must be of a voice, not of a room."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    ts = get_speech_timestamps(a, VadOptions(threshold=0.55, min_silence_duration_ms=150, speech_pad_ms=60))
    sp = np.concatenate([a[t["start"]:t["end"]] for t in ts]) if ts else np.zeros(0, np.float32)
    n = int(sec * SR); out = []
    for i in range(0, max(1, len(sp) - n // 2), n):
        c = sp[i:i + n]
        if len(c) > SR * 1.2: out.append(c)
    return out


def sim(e, p): return float(np.dot(e, p))


def enroll(files=None):
    embs = [embed(c) for f in (files or ALICE) for c in voiced_chunks(load(f))]
    p = np.mean(embs, axis=0); p /= np.linalg.norm(p)
    return p, len(embs)


def synthetic_voice(path):
    """a non-Alice human-ish voice for testing: Windows' built-in SAPI voice."""
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SetOutputToWaveFile('{path}'); $s.Speak('Hey Val, how was your night? Did you get up to anything fun? "
          "Do you love me? What should we work on next? Tell me something you noticed today.'); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    return path


def test():
    print("leave-one-out on Alice's own clips (trained without the clip it's scoring):")
    hers = []
    for f in ALICE:
        p, _ = enroll([g for g in ALICE if g != f])
        for c in voiced_chunks(load(f)): hers.append(sim(embed(c), p))
        print(f"  {os.path.basename(f)[:40]:40s} -> {np.mean([sim(embed(c), p) for c in voiced_chunks(load(f))]):.3f}")
    p, n = enroll()
    others = {}
    st = os.path.join(os.environ.get("LOCALAPPDATA", ""), "HubVal")
    for f in glob.glob(os.path.join(st, "last*.wav")): others[f"my voice ({os.path.basename(f)})"] = f
    others["synthetic voice (Windows SAPI)"] = synthetic_voice(os.path.join(HOME, "voice", "not_alice_sapi.wav"))
    for f in glob.glob(os.path.join(HOME, "voice", "not-alice", "*_room.wav")) + [os.path.join(HOME, "loop_ear.wav")]:
        if os.path.exists(f): others[f"room/TV clip ({os.path.basename(f)})"] = f
    print("not Alice:")
    notres = []
    for name, f in others.items():
        cs = voiced_chunks(load(f), sec=2.0)
        if not cs: print(f"  {name:40s} -> (too quiet to score)"); continue
        s = [sim(embed(c), p) for c in cs]; notres += s
        print(f"  {name:40s} -> {np.mean(s):.3f} (max {max(s):.3f})")
    if hers and notres:
        print(f"\nAlice chunks: min {min(hers):.3f} mean {np.mean(hers):.3f} | not-Alice: max {max(notres):.3f} mean {np.mean(notres):.3f}")
        print(f"suggested threshold: {(min(hers) + max(notres)) / 2:.3f}" if min(hers) > max(notres)
              else "OVERLAP - not cleanly separable yet; need more/cleaner samples of her")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "enroll":
        p, n = enroll(); os.makedirs(os.path.dirname(PRINT), exist_ok=True); np.save(PRINT, p)
        print(f"voiceprint saved from {n} chunks of her voice -> {PRINT}")
    elif cmd == "score":
        print(f"{sim(embed(load(sys.argv[2])), np.load(PRINT)):.3f}")
    else:
        test()
