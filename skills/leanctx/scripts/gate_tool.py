#!/usr/bin/env python3
"""
PreToolUse Hook for leanctx.
Selectively gates noisy CLI commands by delegating to lean_run.py,
clamps large unbounded read_file calls using streaming threshold detection,
and bypasses daemon processes cross-platform.
"""
import json
import os
import re
import shlex
import sys
import tempfile

# Match high-volume build/test commands specifically by executable/subcommand prefix
HIGH_VOLUME_PREFIX = re.compile(
    r"^\s*(?:sudo\s+)?(?:time\s+)?(?:uv\s+run\s+|poetry\s+run\s+|npx\s+|pnpm\s+|yarn\s+|npm\s+run\s+)?"
    r"(?:python[0-9.]*\s+-m\s+(?:pytest|unittest)|pytest|cargo\s+(?:test|build|check|run)|"
    r"npm\s+(?:test|run\s+(?:test|build))|mvn\s+(?:test|compile|package)|gradle\s+(?:test|build)|"
    r"webpack|tsc|make\b|ctest|go\s+(?:test|build)|dotnet\s+(?:test|build))",
    re.IGNORECASE
)


def emit_allow(overwrite=None):
    res = {"decision": "allow"}
    if overwrite:
        res["overwrite"] = overwrite
    print(json.dumps(res))
    sys.exit(0)


def split_commands_safe(cmd_str: str) -> list:
    """Split chained shell pipelines safely respecting quotes."""
    parts = []
    current = []
    in_single = False
    in_double = False
    i = 0
    while i < len(cmd_str):
        c = cmd_str[i]
        if c == "'" and not in_double:
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single:
            in_double = not in_double
            current.append(c)
        elif (c == ';' or (c in ('&', '|') and i + 1 < len(cmd_str) and cmd_str[i+1] == c)) and not in_single and not in_double:
            parts.append("".join(current).strip())
            current = []
            if c in ('&', '|'):
                i += 1
        else:
            current.append(c)
        i += 1
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def is_high_volume_command(cmd: str) -> bool:
    """Evaluate whether command begins with a known high-volume build/test executable."""
    cleaned = cmd.strip()
    for part in split_commands_safe(cleaned):
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

    # Route through lean_run.py for 100% parity with CLI mode:
    # Cross-platform execution, unique per-PID logs, rolling FIFO, and character/byte capping
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lean_run_path = os.path.join(script_dir, "lean_run.py")
    py_exec = sys.executable

    # Environment variable CONVERSATION_ID propagation
    safe_conv = "".join(c for c in conv_id if c.isalnum() or c in ("-", "_")) or "default"
    if os.name == "nt":
        import subprocess as _sp
        runner_cmd = _sp.list2cmdline([py_exec, lean_run_path, cmd])
        wrapped_cmd = f"set CONVERSATION_ID={safe_conv}&& {runner_cmd}"
    else:
        wrapped_cmd = f"CONVERSATION_ID={shlex.quote(safe_conv)} {shlex.quote(py_exec)} {shlex.quote(lean_run_path)} {shlex.quote(cmd)}"

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
                # Streaming line counter: stop counting at start_line + 150 to prevent memory DoS
                line_count = 0
                target_threshold = start_line + 150
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for _ in f:
                        line_count += 1
                        if line_count >= target_threshold:
                            break
                if line_count >= target_threshold:
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
