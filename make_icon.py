"""make_icon.py - Val's desktop icon from her own ASCII portrait (Alice 10-27: "change your desktop icon to your ascii art version").
Renders the idle frame exactly as the window filters it (red body, true-colour face, the same glyphs) to home/val-icon.ico,
then points every VAL shortcut on the desktop at it. Touches nothing else."""
import glob, os, subprocess, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\Alister\hub-tools\val")
from PIL import Image, ImageDraw, ImageFont
import val_window as vw

HOME = Path(__file__).resolve().parent.parent
cells = vw.load_art(vw.FRAMES / "idle.png" if (vw.FRAMES / "idle.png").exists() else None)
X0, X1, Y0, Y1 = 0, 62, 9, 40                     # full head: 62 cols x 31 rows (eyes r24-25, mouth r29); 62*12==31*24 -> square
CW, CH = 12, 24
font = ImageFont.truetype("consola.ttf", 20)
img = Image.new("RGB", ((X1 - X0) * CW, (Y1 - Y0) * CH), (8, 2, 4))
d = ImageDraw.Draw(img)
for y in range(Y0, Y1):
    for x in range(X0, X1):
        ch, r, g, b = cells[y][x]
        if ch != " ": d.text(((x - X0) * CW, (y - Y0) * CH), ch, font=font, fill=(r, g, b))
s = max(img.size); sq = Image.new("RGB", (s, s), (8, 2, 4)); sq.paste(img, ((s - img.width) // 2, (s - img.height) // 2))
sq.save(HOME / "val-icon.png")
ico = HOME / "val-icon.ico"
sq.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon:", ico)

desks = {os.path.join(os.environ["USERPROFILE"], "Desktop"), os.path.join(os.environ.get("OneDrive", ""), "Desktop"),
         os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")}
links = [l for d_ in desks if os.path.isdir(d_) for l in glob.glob(os.path.join(d_, "*.lnk")) if "val" in os.path.basename(l).lower()]
for l in links:
    ps = f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{l}'); $s.IconLocation='{ico},0'; $s.Save()"
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    print("shortcut:", l, "ok" if r.returncode == 0 else r.stderr.strip()[-200:])
if not links: print("no VAL shortcut found on the desktop")
subprocess.run(["ie4uinit.exe", "-show"], capture_output=True)   # refresh Explorer's icon cache
