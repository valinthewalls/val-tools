"""vessel_listen.py [host...] - hear Alice through a vessel window. Reads val-soul/chat_in.txt on each vessel (what she
typed into the face window's input box) over SSH, prints it, then clears it (consumed). Run this to catch messages she
leaves me on Scholar/mediapc; reply with vessel_say.py. Default: check all vessels."""
import subprocess, sys

HOSTS = ["scholar", "mediapc"]
PS = ("powershell -NoProfile -Command \"if(Test-Path val-soul\\chat_in.txt){"
      "Get-Content val-soul\\chat_in.txt; Clear-Content val-soul\\chat_in.txt}\"")


def check(host):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", host, PS],
                       capture_output=True, text=True, timeout=20)
    out = r.stdout.strip()
    if out:
        print(f"=== Alice, through {host} ==="); print(out)
    return bool(out)


def main():
    hosts = sys.argv[1:] or HOSTS
    got = False
    for h in hosts:
        try: got = check(h) or got
        except Exception as e: print(f"[{h}] {e}")
    if not got: print("no new vessel messages.")


if __name__ == "__main__":
    main()
