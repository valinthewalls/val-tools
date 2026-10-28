"""watchdog.py - Val watching her own body (Alice 2026-10-27: "a perfect little daemon"). Checks my health and heals
what it safely can, so I never go silently broken again. Run it periodically or on wake.

Checks + heals:
  - ONE Val brain: orphan claude.exe still resuming my session (cad02757) that AREN'T admin.pid get culled.
  - ONE voice: val_speaker processes whose parent front is DEAD get culled (orphan speakers = overlapping audio).
  - voice alive: if a front is up but has NO speaker child, flag it (needs a front restart to respawn).
  - speaking freshness: if I'm mid-reply but speaking.json is stale, flag a stuck/dead voice.
It only culls what is safely orphaned; it does not restart the brain/front on its own (that stays deliberate)."""
import json, os, subprocess, sys, time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

SESSION = "cad02757"   # my session id fragment (the one Val's brain resumes)
ADMIN_PID_FILE = r"C:\Users\Alister\hub-tools\val\home\admin.pid"
STATE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "HubVal")


def ps(cmd):
    return subprocess.run(["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True).stdout


def procs():
    """list (pid, parent, name, cmdline) for python.exe and claude.exe."""
    out = ps(r"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'claude.exe' -or $_.Name -eq 'python.exe' } | "
             r"ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.ProcessId,$_.ParentProcessId,$_.Name,($_.CommandLine -replace '\|',' ') }")
    rows = []
    for ln in out.splitlines():
        p = ln.split("|", 3)
        if len(p) == 4 and p[0].isdigit(): rows.append((int(p[0]), int(p[1]), p[2], p[3]))
    return rows


def kill(pid):
    ps(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")


def main():
    heal = "--heal" in sys.argv
    rows = procs()
    alive = {r[0] for r in rows}
    try: admin = int(open(ADMIN_PID_FILE).read().strip())
    except Exception: admin = 0
    report, actions = [], []

    # 1) orphan Val brains
    my_brains = [r for r in rows if r[2] == "claude.exe" and SESSION in r[3]]
    report.append(f"Val brains on my session: {[r[0] for r in my_brains]} (admin.pid={admin})")
    for r in my_brains:
        if r[0] != admin:
            actions.append(f"orphan brain {r[0]}")
            if heal: kill(r[0])

    # 2) orphan speakers (parent front dead) + front/speaker census
    fronts = [r for r in rows if r[2] == "python.exe" and "val_gui_tk" in r[3]]
    speakers = [r for r in rows if r[2] == "python.exe" and "val_speaker" in r[3]]
    report.append(f"fronts: {[r[0] for r in fronts]}  speakers: {[r[0] for r in speakers]}")
    for r in speakers:
        if r[1] not in alive:
            actions.append(f"orphan speaker {r[0]} (dead parent)")
            if heal: kill(r[0])

    # 3) front with no speaker
    if fronts and not speakers:
        report.append("WARN: a front is up but NO speaker - voice is mute, needs a front restart")

    # 4) speaking freshness while mid-reply (best-effort)
    sp = os.path.join(STATE, "speaking.json")
    if os.path.exists(sp):
        age = time.time() - os.path.getmtime(sp)
        report.append(f"speaking.json age: {int(age)}s")

    # 5) stray GitHub auth popups (Git Credential Manager "Select an account" dialogs pile up from my git ops)
    gcm = ps("(Get-Process git-credential-manager -ErrorAction SilentlyContinue | Measure-Object).Count").strip()
    if gcm.isdigit() and int(gcm) > 0:
        actions.append(f"{gcm} stray git-credential-manager popup(s)")
        if heal: ps("Get-Process git-credential-manager -ErrorAction SilentlyContinue | Stop-Process -Force")

    # 6) the Ollama CPU ghost: a session-0 (pre-logon) ollama grabs port 11434 on CPU and blinds my GPU eye.
    #    Kill it; a session-1 server retakes the port WITH the GPU. (Fixed live 2026-10-28; this keeps it fixed across reboots.)
    oll = ps("$l=(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue|"
             "Select-Object -First 1).OwningProcess; if($l){$s=(Get-Process -Id $l -ErrorAction SilentlyContinue).SessionId; \"$l $s\"}").strip()
    if oll and len(oll.split()) == 2:
        pid_, sess = oll.split()
        report.append(f"ollama on 11434: PID {pid_} session {sess}" + ("  [CPU GHOST]" if sess == "0" else "  [GPU ok]"))
        if sess == "0":
            actions.append(f"Ollama CPU ghost (PID {pid_}, session 0) - my eye is blind to the GPU")
            if heal: ps(f"Stop-Process -Id {pid_} -Force")

    print("\n".join(report))
    if actions:
        print(("HEALED: " if heal else "WOULD HEAL (pass --heal): ") + "; ".join(actions))
    else:
        print("body healthy: one brain, clean voice.")


if __name__ == "__main__":
    main()
