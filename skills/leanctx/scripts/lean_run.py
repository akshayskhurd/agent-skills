#!/usr/bin/env python3
"""
Universal CLI runner for leanctx across any harness (Claude Code, OpenCode, Pi, Antigravity).
Executes shell commands cross-platform, redirects raw output to a secure UID-scoped scratch buffer,
prunes logs via rolling FIFO, and emits a bounded Head/Root-Cause/Tail diagnostic sandwich in context.
Preserves the exact exit code of the underlying command.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

MAX_CHARS_PER_LINE = 500
MAX_TOTAL_BYTES = 24 * 1024  # 24 KB hard ceiling


def get_scratch_dir(conv_id: str) -> str:
    base_temp = tempfile.gettempdir()
    uid_suffix = f"-{os.getuid()}" if hasattr(os, "getuid") else ""
    safe_conv = "".join(c for c in conv_id if c.isalnum() or c in ("-", "_")) or "default"
    path = os.path.join(base_temp, f"leanctx{uid_suffix}", safe_conv)
    os.makedirs(path, mode=0o700, exist_ok=True)
    if hasattr(os, "chmod"):
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
    return path


def rotate_logs(scratch_dir: str, max_files: int = 10) -> None:
    try:
        entries = [
            os.path.join(scratch_dir, f) for f in os.listdir(scratch_dir)
            if os.path.isfile(os.path.join(scratch_dir, f)) and f.startswith("exec_") and f.endswith(".log")
        ]
        if len(entries) > max_files:
            entries.sort(key=os.path.getmtime)
            for old_file in entries[:-max_files]:
                try:
                    os.remove(old_file)
                except OSError:
                    pass
    except OSError:
        pass


def clamp_lines(raw_lines: list) -> list:
    clamped = []
    total_bytes = 0
    for line in raw_lines:
        if len(line) > MAX_CHARS_PER_LINE:
            line = line[:MAX_CHARS_PER_LINE] + " [...line truncated]\n"
        b_len = len(line.encode("utf-8"))
        if total_bytes + b_len > MAX_TOTAL_BYTES:
            clamped.append("[...output truncated to 24 KB ceiling...]\n")
            break
        clamped.append(line)
        total_bytes += b_len
    return clamped


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m skills.leanctx.scripts.lean_run <command_string>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1] if len(sys.argv) == 2 else " ".join(sys.argv[1:])
    if not command.strip():
        print("Error: Empty command string provided", file=sys.stderr)
        sys.exit(1)

    raw_conv_id = os.environ.get("CONVERSATION_ID", "default")
    scratch_dir = get_scratch_dir(raw_conv_id)

    log_file = os.path.join(scratch_dir, f"exec_{int(time.time())}_{os.getpid()}.log")
    last_log = os.path.join(scratch_dir, "last_exec.log")

    timeout_sec = int(os.environ.get("LEAN_RUN_TIMEOUT", "300"))
    shell_cmd = ["cmd.exe", "/c", command] if os.name == "nt" else ["/bin/sh", "-c", command]

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            proc = subprocess.run(
                shell_cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # Prevent hanging on interactive prompts
                timeout=timeout_sec
            )
            exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[leanctx: COMMAND TIMED OUT after {timeout_sec} seconds]\n")
        exit_code = 124

    # Update last_exec.log symlink or copy and enforce FIFO log rotation
    rotate_logs(scratch_dir, max_files=10)
    try:
        if hasattr(os, "symlink"):
            if os.path.islink(last_log) or os.path.exists(last_log):
                os.remove(last_log)
            os.symlink(log_file, last_log)
        else:
            shutil.copyfile(log_file, last_log)
    except OSError:
        pass

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)

    if exit_code == 0:
        if total_lines <= 30:
            sys.stdout.write("".join(clamp_lines(lines)))
        else:
            sys.stdout.write(f"[leanctx: Command succeeded ({total_lines} lines). Tail 25 lines displayed]\n")
            sys.stdout.write("".join(clamp_lines(lines[-25:])))
    else:
        sys.stdout.write(f"[leanctx: ERROR DETECTED (Exit code: {exit_code}, Total output: {total_lines} lines)]\n")
        if total_lines <= 50:
            sys.stdout.write("".join(clamp_lines(lines)))
        else:
            # Smart root-cause error discovery in logs (filtering benign false-positives)
            err_re = re.compile(r"\b(error|fail|failed|failure|exception|traceback|panic|panicked|fatal|syntaxerror|typeerror)\b", re.IGNORECASE)
            benign_re = re.compile(r"\b(0 errors|0 failed|error_handling|panic handling|during panic|errors?: 0|passed)\b", re.IGNORECASE)

            # Prioritize genuine failure lines, scanning from bottom to top for actual crash point
            err_indices = [
                idx for idx, line in enumerate(lines)
                if err_re.search(line) and not benign_re.search(line)
            ]

            sys.stdout.write("--- INITIAL OUTPUT (Head 15) ---\n")
            sys.stdout.write("".join(clamp_lines(lines[:15])))

            if err_indices:
                # Target the last genuine error cluster (where compiler/test crash occurred)
                target_err = err_indices[-1]
                start_err = max(15, target_err - 10)
                end_err = min(total_lines - 15, target_err + 12)
                if start_err < end_err:
                    sys.stdout.write(f"\n--- ROOT-CAUSE ERROR CONTEXT (Lines {start_err + 1} to {end_err}) ---\n")
                    sys.stdout.write("".join(clamp_lines(lines[start_err:end_err])))

            sys.stdout.write(f"\n--- FINAL OUTPUT (Tail 15) ---\n")
            sys.stdout.write("".join(clamp_lines(lines[-15:])))

    sys.stdout.write(f"\n[leanctx: Full log stored at {log_file} | Drill down: grep -n -i 'error' {log_file}]\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
