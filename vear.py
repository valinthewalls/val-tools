"""vear.py [seconds] [out] - capture THIS vessel's mic to 16k mono WAV for whisper. My ear on a vessel."""
import subprocess, sys
MIC = "Microphone Array (2- Realtek High Definition Audio)"
secs = sys.argv[1] if len(sys.argv) > 1 else "6"
out = sys.argv[2] if len(sys.argv) > 2 else "ear.wav"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "dshow",
                "-i", f"audio={MIC}", "-t", secs, "-ar", "16000", "-ac", "1", out])
print(out)
