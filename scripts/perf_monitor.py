#!/usr/bin/env python3
"""
apple-murmur performance monitor.

Samples CPU, memory, and Apple Neural Engine (ANE) utilisation while the
murmur daemon is running.  Prints a live table and writes a JSON summary on exit.

Usage:
    # Basic (no ANE — no sudo required):
    python3 scripts/perf_monitor.py

    # With ANE metrics (requires sudo):
    sudo python3 scripts/perf_monitor.py --ane

    # Custom interval / output file:
    python3 scripts/perf_monitor.py --interval 0.5 --out /tmp/perf.json
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

try:
    import psutil
except ImportError:
    sys.exit("psutil is required: pip install psutil")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
PHASES = ("idle", "recording", "transcribing")
_samples: Dict[str, List[dict]] = defaultdict(list)
_current_phase = "idle"
_lock = threading.Lock()
_stop_event = threading.Event()

# PID of the murmur daemon, discovered at startup
_murmur_pid: Optional[int] = None


def _find_murmur_pid() -> Optional[int]:
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
            if "murmur.daemon" in cmd or "murmur/daemon.py" in cmd:
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


# ---------------------------------------------------------------------------
# ANE sampler (powermetrics, requires sudo)
# ---------------------------------------------------------------------------
_ane_latest: float = 0.0
_ane_thread: Optional[threading.Thread] = None


def _start_ane_sampler(interval_ms: int = 500) -> None:
    """Launch powermetrics in background and parse ANE utilisation lines."""
    global _ane_thread

    def _run():
        global _ane_latest
        cmd = [
            "sudo", "powermetrics",
            "--samplers", "cpu_power",
            "-i", str(interval_ms),
            "--format", "plist",
        ]
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            buf = []
            for line in proc.stdout:
                if _stop_event.is_set():
                    proc.terminate()
                    break
                buf.append(line)
                # powermetrics emits one plist per sample separated by a NUL byte;
                # parse simple ANE line instead of full plist for speed
                m = re.search(r"ANE\s+Power:\s*([\d.]+)\s*mW", line)
                if m:
                    _ane_latest = float(m.group(1))
        except Exception:
            pass

    _ane_thread = threading.Thread(target=_run, daemon=True, name="ane-sampler")
    _ane_thread.start()


# ---------------------------------------------------------------------------
# Sampler loop
# ---------------------------------------------------------------------------
def _sample_loop(interval: float, ane: bool) -> None:
    proc: psutil.Process | None = None

    while not _stop_event.is_set():
        ts = time.time()

        # Try to (re)attach to the daemon process
        if proc is None and _murmur_pid:
            try:
                proc = psutil.Process(_murmur_pid)
            except psutil.NoSuchProcess:
                pass

        # System-wide metrics
        cpu_sys = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()

        # Process-level metrics
        proc_cpu = 0.0
        proc_rss_mb = 0.0
        if proc:
            try:
                proc_cpu = proc.cpu_percent(interval=None)
                proc_rss_mb = proc.memory_info().rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc = None

        sample = {
            "ts": ts,
            "cpu_sys_pct": cpu_sys,
            "mem_used_pct": mem.percent,
            "mem_used_mb": (mem.total - mem.available) / 1024 / 1024,
            "proc_cpu_pct": proc_cpu,
            "proc_rss_mb": proc_rss_mb,
        }
        if ane:
            sample["ane_mw"] = _ane_latest

        with _lock:
            _samples[_current_phase].append(sample)

        _print_live(sample)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# Live display
# ---------------------------------------------------------------------------
_header_printed = False


def _print_live(s: dict) -> None:
    global _header_printed
    if not _header_printed:
        ane_col = "  ANE(mW)" if "ane_mw" in s else ""
        print(
            f"{'Timestamp':<12}  {'Phase':<13}  {'SysCPU%':>8}  "
            f"{'Mem%':>6}  {'ProcCPU%':>9}  {'ProcRSS(MB)':>11}{ane_col}"
        )
        print("-" * (75 + (10 if "ane_mw" in s else 0)))
        _header_printed = True

    ane_col = f"  {s['ane_mw']:>8.1f}" if "ane_mw" in s else ""
    ts = datetime.fromtimestamp(s["ts"]).strftime("%H:%M:%S.%f")[:-3]
    print(
        f"{ts:<12}  {_current_phase:<13}  {s['cpu_sys_pct']:>8.1f}  "
        f"{s['mem_used_pct']:>6.1f}  {s['proc_cpu_pct']:>9.1f}  "
        f"{s['proc_rss_mb']:>11.1f}{ane_col}"
    )


# ---------------------------------------------------------------------------
# Phase control — murmur daemon writes state to log; we watch a trigger file
# ---------------------------------------------------------------------------
_PHASE_FILE = "/tmp/murmur_monitor_phase"


def _watch_phase_file() -> None:
    """Poll a small trigger file that external tooling can write to set phase."""
    global _current_phase
    last_mtime = 0.0
    while not _stop_event.is_set():
        try:
            mtime = os.path.getmtime(_PHASE_FILE)
            if mtime != last_mtime:
                last_mtime = mtime
                phase = open(_PHASE_FILE).read().strip().lower()
                if phase in PHASES:
                    with _lock:
                        _current_phase = phase
        except FileNotFoundError:
            pass
        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def _summarise(ane: bool) -> dict:
    def _stats(vals):
        if not vals:
            return {}
        return {
            "count": len(vals),
            "mean": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
        }

    summary = {}
    with _lock:
        for phase, samples in _samples.items():
            summary[phase] = {
                "cpu_sys_pct":   _stats([s["cpu_sys_pct"] for s in samples]),
                "mem_used_pct":  _stats([s["mem_used_pct"] for s in samples]),
                "proc_cpu_pct":  _stats([s["proc_cpu_pct"] for s in samples]),
                "proc_rss_mb":   _stats([s["proc_rss_mb"] for s in samples]),
            }
            if ane:
                summary[phase]["ane_mw"] = _stats([s["ane_mw"] for s in samples])
    return summary


def _print_summary(summary: dict, out_path: Optional[str], ane: bool) -> None:
    print("\n\n=== PERFORMANCE SUMMARY ===\n")
    metrics = ["cpu_sys_pct", "mem_used_pct", "proc_cpu_pct", "proc_rss_mb"]
    if ane:
        metrics.append("ane_mw")

    for phase in PHASES:
        if phase not in summary:
            continue
        print(f"  [{phase.upper()}]")
        for m in metrics:
            s = summary[phase].get(m, {})
            if not s:
                continue
            print(
                f"    {m:<16}  n={s['count']:>4}  "
                f"mean={s['mean']:>8.2f}  min={s['min']:>8.2f}  max={s['max']:>8.2f}"
            )
        print()

    if out_path:
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary written to {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    global _murmur_pid

    parser = argparse.ArgumentParser(description="apple-murmur performance monitor")
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Sampling interval in seconds (default: 0.5)")
    parser.add_argument("--ane", action="store_true",
                        help="Include ANE metrics via powermetrics (requires sudo)")
    parser.add_argument("--out", default=None, dest="out",
                        help="Write JSON summary to this path on exit")
    parser.add_argument("--pid", type=int, default=None,
                        help="Murmur daemon PID (auto-detected if omitted)")
    args = parser.parse_args()

    # Discover daemon
    _murmur_pid = args.pid or _find_murmur_pid()
    if _murmur_pid:
        print(f"Attached to murmur daemon PID {_murmur_pid}")
    else:
        print("murmur daemon not running — monitoring system-wide metrics only")
        print("Start with: murmur start")
        print("(will auto-attach if daemon starts while monitor is running)")

    # Phase trigger instructions
    print(f"\nTo mark phases, write to {_PHASE_FILE}:")
    for p in PHASES:
        print(f"  echo {p} > {_PHASE_FILE}")
    print()

    if args.ane:
        _start_ane_sampler(interval_ms=int(args.interval * 1000))
        time.sleep(0.5)  # let powermetrics settle

    # Prime cpu_percent (first call returns 0.0)
    psutil.cpu_percent(interval=None)
    if _murmur_pid:
        try:
            psutil.Process(_murmur_pid).cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(args.interval)

    phase_thread = threading.Thread(target=_watch_phase_file, daemon=True, name="phase-watcher")
    phase_thread.start()

    def _shutdown(sig, frame):
        print("\nStopping...")
        _stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _sample_loop(args.interval, args.ane)

    summary = _summarise(args.ane)
    _print_summary(summary, args.out, args.ane)


if __name__ == "__main__":
    main()
