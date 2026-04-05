import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

PID_FILE = Path.home() / ".apple-murmur" / "murmur.pid"
LOG_FILE = Path.home() / ".apple-murmur" / "murmur.log"


def cmd_start(args) -> None:
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            print(f"murmur is already running (PID {pid})")
            return
        except ProcessLookupError:
            PID_FILE.unlink()

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    install_dir = Path.home() / ".apple-murmur"
    with open(LOG_FILE, "a") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "murmur.daemon"],
            stdout=log,
            stderr=log,
            start_new_session=True,
            cwd=str(install_dir),
        )
    PID_FILE.write_text(str(proc.pid))
    print(f"murmur started (PID {proc.pid})")


def cmd_stop(args) -> None:
    if not PID_FILE.exists():
        print("murmur is not running")
        return
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink()
        print(f"murmur stopped (PID {pid})")
    except ProcessLookupError:
        PID_FILE.unlink()
        print("murmur was not running (cleaned up stale PID file)")


def cmd_status(args) -> None:
    if not PID_FILE.exists():
        print("murmur: stopped")
        return
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        print(f"murmur: running (PID {pid})")
    except ProcessLookupError:
        PID_FILE.unlink()
        print("murmur: stopped (stale PID file cleaned up)")


def cmd_update(args) -> None:
    install_dir = Path.home() / ".apple-murmur"
    was_running = PID_FILE.exists()
    if was_running:
        cmd_stop(args)
    subprocess.run(["git", "pull"], cwd=install_dir, check=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(install_dir / "requirements.txt")],
        check=True,
    )
    if was_running:
        cmd_start(args)


def main() -> None:
    parser = argparse.ArgumentParser(prog="murmur", description="Local voice-to-text daemon")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="Start the daemon")
    sub.add_parser("stop", help="Stop the daemon")
    sub.add_parser("status", help="Show daemon status")
    sub.add_parser("update", help="Pull latest version and restart")
    args = parser.parse_args()
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "update": cmd_update,
    }
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
