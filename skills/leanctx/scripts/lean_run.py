#!/usr/bin/env python3
"""
Universal CLI runner for leanctx across any harness (Claude Code, OpenCode, Pi, Antigravity).
Executes shell commands, redirects raw output to a secure scratch buffer (mode 0700),
and emits a bounded Head/Tail diagnostic sandwich in context.
Preserves the exact exit code of the underlying command.
"""
import argparse
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m skills.leanctx.scripts.lean_run <command_string>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1] if len(sys.argv) == 2 else " ".join(sys.argv[1:])
    if not command.strip():
        print("Error: Empty command string provided", file=sys.stderr)
        sys.exit(1)

    raw_conv_id = os.environ.get("CONVERSATION_ID", "default")
    conv_id = "".join(c for c in raw_conv_id if c.isalnum() or c in ("-", "_")) or "default"
    scratch_dir = f"/tmp/leanctx/{conv_id}"
    os.makedirs(scratch_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(scratch_dir, 0o700)
    except OSError:
        pass

    log_file = os.path.join(scratch_dir, "last_exec.log")

    timeout_sec = int(os.environ.get("LEAN_RUN_TIMEOUT", "300"))
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            proc = subprocess.run(["/bin/sh", "-c", command], stdout=f, stderr=subprocess.STDOUT, timeout=timeout_sec)
            exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[leanctx: COMMAND TIMED OUT after {timeout_sec} seconds]\n")
        exit_code = 124

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)

    if exit_code == 0:
        if total_lines <= 30:
            sys.stdout.write("".join(lines))
        else:
            sys.stdout.write(f"[leanctx: Command succeeded ({total_lines} lines). Tail 25 lines displayed]\n")
            sys.stdout.write("".join(lines[-25:]))
    else:
        sys.stdout.write(f"[leanctx: ERROR DETECTED (Exit code: {exit_code}, Total output: {total_lines} lines)]\n")
        if total_lines <= 50:
            sys.stdout.write("".join(lines))
        else:
            sys.stdout.write("--- INITIAL OUTPUT (Head 25) ---\n")
            sys.stdout.write("".join(lines[:25]))
            sys.stdout.write(f"\n... [{total_lines - 50} lines truncated by leanctx] ...\n\n")
            sys.stdout.write("--- FINAL OUTPUT (Tail 25) ---\n")
            sys.stdout.write("".join(lines[-25:]))

    sys.stdout.write(f"[leanctx: Full raw log stored at {log_file}]\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
