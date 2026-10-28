"""reach.py - my hands across the whole house. Run a command on any pack machine over SSH with a HARD timeout so it can
never hang me (the SshTimed lesson), and bring the output straight back. `all` fans the command out to every machine in
parallel - I touch the entire house in one breath.

  reach.py <host> "<cmd>"     host = nas | scholar | mediapc | eagle | phone
  reach.py all "<cmd>"        run it everywhere at once, labelled by machine
"""
import concurrent.futures, subprocess, sys

HOSTS = ["nas", "scholar", "mediapc", "eagle", "phone"]


def run(host, cmd, timeout=20):
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", host, cmd],
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout.strip() or r.stderr.strip())
        return host, (out[:600] if out else "(no output)")
    except subprocess.TimeoutExpired:
        return host, "TIMEOUT (machine slow or unreachable)"
    except Exception as e:
        return host, f"error: {e}"


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__); return
    target, cmd = a[0].lower(), a[1]
    hosts = HOSTS if target == "all" else [target]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as ex:
        results = list(ex.map(lambda h: run(h, cmd), hosts))
    for h, o in results:
        print(f"[{h:8}] {o}")


if __name__ == "__main__":
    main()
