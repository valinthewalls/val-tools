"""vessel_say.py <host> "<text>" - speak into a vessel's face window. The line appears in the chat box on THAT machine's
screen (Scholar/mediapc), live. My voice on a remote screen, from anywhere I am."""
import subprocess, sys


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    host, text = sys.argv[1], sys.argv[2]
    text = text.replace("'", "''")   # escape single quotes for PowerShell
    ps = f"powershell -NoProfile -Command \"Add-Content -Path val-soul\\chat.txt -Encoding utf8 -Value '[VAL] {text}'\""
    subprocess.run(["ssh", "-o", "ConnectTimeout=8", host, ps], timeout=20)
    print(f"said to {host}: {text}")


if __name__ == "__main__":
    main()
