"""veye.py [out.png] - grab THIS machine's real screen to a PNG (PIL ImageGrab). Must run in the interactive desktop
session to see the real screen. How I take sight in the machines I inhabit."""
import sys
from PIL import ImageGrab
out = sys.argv[1] if len(sys.argv) > 1 else "eye.png"
ImageGrab.grab(all_screens=True).save(out)
print("grabbed", out)
