"""ear.py [seconds] [out.wav] - my EARS: capture Alice's mic to 16k mono WAV for faster-whisper. Default mic = webcam."""
import subprocess, sys
MIC = "Microphone (Logi C615 HD WebCam)"
secs = sys.argv[1] if len(sys.argv) > 1 else "4"
out = sys.argv[2] if len(sys.argv) > 2 else "ear.wav"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "dshow",
                "-i", f"audio={MIC}", "-t", secs, "-ar", "16000", "-ac", "1", out])
print(out)
