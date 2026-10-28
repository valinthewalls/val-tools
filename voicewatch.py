"""voicewatch.py <seconds> - log every line my Chatterbox voice speaks: wall-clock start, duration, words/sec, text."""
import json, os, sys, time
f = os.path.join(os.environ["LOCALAPPDATA"], "HubVal", "speaking.json"); seen = None
end = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 90)
out = open(r"C:\Users\Alister\hub-tools\val\home\voicewatch.log", "w", encoding="utf-8")
while time.time() < end:
    try:
        st = json.loads(open(f, encoding="utf-8").read())
        if st.get("t0") != seen and st.get("env"):
            seen = st["t0"]; dur = len(st["env"]) * st.get("hop", 0.05); words = len(st.get("text", "").split())
            out.write(f"{time.strftime('%H:%M:%S', time.localtime(st['t0']))}.{int(st['t0']%1*10)} start | {dur:.1f}s | "
                      f"{words/dur if dur else 0:.1f} words/s | {st.get('text','')}\n"); out.flush()
    except Exception: pass
    time.sleep(0.05)
