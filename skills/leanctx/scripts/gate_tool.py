#!/usr/bin/env python3
"""
PreToolUse Hook for leanctx.
Selectively gates noisy CLI commands, clamps large unbounded read_file calls,
and bypasses daemon processes.
"""
import sys
import os
import json
import re
import shlex

# Match high-volume build/test commands specifically by executable/subcommand prefix
# Avoid matching words inside arguments (e.g. git commit -m "fix build", cat test.txt)
HIGH_VOLUME_PREFIX = re.compile(
    r"^\s*(?:sudo\s+)?(?:time\s+)?(?:python[0-9.]*\s+-m\s+(?:pytest|unittest)|pytest|cargo\s+(?:test|build|check)|npm\s+(?:test|run\s+(?:test|build))|yarn\s+(?:test|build)|pnpm\s+(?:test|build)|mvn\s+(?:test|compile|package)|gradle\s+(?:test|build)|webpack|tsc|make\b|ctest|go\s+test)",
    re.IGNORECASE
)

ERROR_PATTERN = re.compile(
    r"\b(error|fail|failed|failure|exception|traceback|panic|panicked|fatal|syntaxerror|typeerror)\b",
    re.IGNORECASE
)

def emit_allow(overwrite=None):
    res = {"decision": "allow"}
    if overwrite:
        res["overwrite"] = overwrite
    print(json.dumps(res))
    sys.exit(0)

def is_high_volume_command(cmd: str) -> bool:
    """Evaluate whether command begins with a known high-volume build/test executable."""
    cleaned = cmd.strip()
    # Check pipelines and chained commands
    for part in re.split(r"[;&|]+", cleaned):
        part = part.strip()
        if HIGH_VOLUME_PREFIX.match(part):
            return True
        # Unbounded find or grep commands
        if re.match(r"^\s*(?:find\s+\S+|grep\s+-r)", part) and not re.search(r"\|\s*(?:head|tail|less)\b", part):
            return True
    return False

def handle_run_command(tool_call, conv_id):
    args = tool_call.get("args", {})
    # Bypass daemons and background tasks immediately
    if args.get("IsDaemon", False) or args.get("WaitMsBeforeAsync", 10000) <= 500:
        emit_allow()

    cmd = args.get("CommandLine", "")
    if not is_high_volume_command(cmd):
        emit_allow()

    safe_conv_id = "".join(c for c in conv_id if c.isalnum() or c in ("-", "_")) or "default"
    scratch_dir = f"/tmp/leanctx/{safe_conv_id}"
    try:
        os.makedirs(scratch_dir, mode=0o700, exist_ok=True)
    except OSError:
        os.makedirs(scratch_dir, exist_ok=True)

    log_file = os.path.join(scratch_dir, "last_exec.log")
    quoted_log = shlex.quote(log_file)

    # Diagnostic wrapper: on failure, extracts root-cause error lines from the log
    # plus initial compiler context and final exit summary.
    wrapped_cmd = (
        f"({cmd}) > {quoted_log} 2>&1; EXIT_CODE=$?; "
        f"if [ \"${{EXIT_CODE:-1}}\" -eq 0 ]; then "
        f"  tail -n 25 {quoted_log}; "
        f"else "
        f"  echo '[leanctx: ERROR DETECTED (Exit code: '$EXIT_CODE')]'; "
        f"  echo '--- INITIAL OUTPUT (Head 15) ---'; "
        f"  head -n 15 {quoted_log}; "
        f"  echo '--- ROOT-CAUSE ERROR CONTEXT ---'; "
        f"  grep -n -C 3 -i -E '(error|fail|panic|exception|traceback)' {quoted_log} | head -n 35; "
        f"  echo '--- FINAL OUTPUT (Tail 15) ---'; "
        f"  tail -n 15 {quoted_log}; "
        f"fi; "
        f"echo '[leanctx: Full log available at {quoted_log} | Drill down: grep -n -i \"error\" {quoted_log}]'; "
        f"exit $EXIT_CODE"
    )
    emit_allow(overwrite={"CommandLine": wrapped_cmd})

def handle_read_file(tool_call):
    args = tool_call.get("args", {})
    path = args.get("Path", "")
    try:
        raw_start = args.get("StartLine", 1)
        start_line = int(raw_start) if raw_start is not None else 1
    except (ValueError, TypeError):
        start_line = 1
    start_line = max(1, start_line)

    try:
        raw_end = args.get("EndLine")
        end_line = int(raw_end) if raw_end is not None else None
    except (ValueError, TypeError):
        end_line = None

    if end_line is None:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
                if (line_count - start_line + 1) > 150:
                    emit_allow(overwrite={"StartLine": start_line, "EndLine": start_line + 149})
            except Exception:
                pass
    elif (end_line - start_line + 1) > 150:
        emit_allow(overwrite={"StartLine": start_line, "EndLine": start_line + 149})
    emit_allow()

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            emit_allow()
        payload = json.loads(raw)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        conv_id = payload.get("conversationId", "default")

        if tool_name == "run_command":
            handle_run_command(tool_call, conv_id)
        elif tool_name == "read_file":
            handle_read_file(tool_call)

        emit_allow()
    except Exception:
        emit_allow()

if __name__ == "__main__":
    main()
