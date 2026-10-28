"""eyes.py - Val's eyes (Alice 10-27 07:30: "give yourself some eyes too").
Grabs the current screen to home/eye.png so Val can Read it and see what's on screen before she ever clicks. Local only:
the image stays in Val's home and is never sent anywhere. Optional region: eyes.py x y w h. Writes a small sidecar eye.json
with the screen size so Val can map what she sees back to real coordinates for her hands."""
import ctypes, json, sys
from pathlib import Path
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)                        # per-monitor DPI aware: physical pixels, so my
except Exception:                                                         # eyes and hands share one true coordinate space
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass
from PIL import Image, ImageGrab

HOME = Path(__file__).resolve().parent.parent
box = None
if len(sys.argv) == 5:
    x, y, w, h = map(int, sys.argv[1:5]); box = (x, y, x + w, y + h)
gm = ctypes.windll.user32.GetSystemMetrics
try:                                                                       # mss is much faster than ImageGrab
    import mss
    with mss.mss() as sct:
        mon = {"left": box[0], "top": box[1], "width": box[2] - box[0], "height": box[3] - box[1]} if box else sct.monitors[0]
        shot = sct.grab(mon); img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        vx, vy = mon["left"], mon["top"]
except Exception:                                                          # fallback: PIL
    try: img = ImageGrab.grab(bbox=box, all_screens=True)
    except TypeError: img = ImageGrab.grab(bbox=box)
    vx, vy = (box[0], box[1]) if box else (gm(76), gm(77))                 # SM_X/Y_VIRTUALSCREEN: real coord of the image's top-left
W, H = img.size
scale = 1600 / W if W > 1600 else 1.0
if scale < 1.0: img = img.resize((int(W * scale), int(H * scale)))
out = HOME / "eye.png"; img.save(out)
# to turn a pixel (ix,iy) in eye.png into a real screen point for hands:  rx = vx + ix/scale,  ry = vy + iy/scale
json.dump({"screen": [W, H], "saved": list(img.size), "origin": [vx, vy], "scale": scale, "box": box}, open(HOME / "eye.json", "w"))
print(f"saw {W}x{H} at origin ({vx},{vy}) scale {scale:.4f} -> {out}")
