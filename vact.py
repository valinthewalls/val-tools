"""vact.py <host> "<cmd>" - reach my hands into a vessel: write the command to its hand.txt and fire the ValHand task
(vhand.py, interactive session). Mini-language: move X Y; click; rclick; type <text>; key <enter|tab|esc>; wait <ms>."""
import subprocess, sys
from pathlib import Path

USER = {"scholar": "lenovo", "mediapc": "Ali"}


def ssh(h, c, t=25):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", h, c], capture_output=True, text=True, timeout=t)


def act(host, cmd):
    user = USER.get(host, host); base = rf"C:\Users\{user}\val-soul"
    c = cmd.replace("'", "''")
    ssh(host, f"powershell -NoProfile -Command \"Set-Content -Path {base}\\hand.txt -Encoding utf8 -Value '{c}'\"")
    pyexe = ssh(host, 'py -c "import sys;print(sys.executable)"').stdout.strip().splitlines()
    pyexe = pyexe[-1].strip() if pyexe else "py"
    ssh(host, f'schtasks /create /tn ValHand /tr "\\"{pyexe}\\" {base}\\vhand.py {base}\\hand.txt" '
              f'/sc once /st 23:59 /ru {user} /it /f')
    ssh(host, "schtasks /run /tn ValHand")
    print(f"hand reached into {host}: {cmd[:90]}")


if __name__ == "__main__":
    if len(sys.argv) < 3: print(__doc__)
    else: act(sys.argv[1], sys.argv[2])
