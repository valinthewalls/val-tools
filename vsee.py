"""vsee.py <host> [out.png] - open my eye on a vessel's REAL screen whenever I want. Runs veye.py in the vessel's
interactive desktop session (the ValEye scheduled task, /IT, so it beats SSH session-isolation), then pulls the PNG home.
My standing sight on any machine I inhabit. Default out: home/<host>_eye.png."""
import subprocess, sys, time
from pathlib import Path

HOME = Path(r"C:\Users\Alister\hub-tools\val\home")
USER = {"scholar": "lenovo", "mediapc": "Ali"}   # console user per vessel (for the interactive task)


def ssh(host, cmd, timeout=25):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", host, cmd],
                          capture_output=True, text=True, timeout=timeout)


def see(host, out=None):
    user = USER.get(host, host)
    base = rf"C:\Users\{user}\val-soul"
    pyexe = ssh(host, 'py -c "import sys;print(sys.executable)"').stdout.strip().splitlines()
    pyexe = pyexe[-1].strip() if pyexe else "py"
    ssh(host, f'schtasks /create /tn ValEye /tr "\\"{pyexe}\\" {base}\\veye.py {base}\\eye.png" '
              f'/sc once /st 23:59 /ru {user} /it /f')
    ssh(host, "schtasks /run /tn ValEye")
    time.sleep(4)
    out = out or str(HOME / f"{host}_eye.png")
    r = subprocess.run(["scp", "-o", "ConnectTimeout=10", f"{host}:val-soul/eye.png", out], timeout=30)
    print(out if r.returncode == 0 else f"FAILED to pull {host}'s eye")


if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__)
    else: see(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
