#!/usr/bin/env python3
"""
PostToolUse Hook for leanctx.
Atomically updates .agents/memory/LEDGER.json for master session only.
Preserves existing public symbol signatures and enforces advisory file locking.
"""
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path


def fail_open():
    print(json.dumps({}))
    sys.exit(0)


@contextlib.contextmanager
def file_lock(lock_path: str):
    """Advisory file locking to prevent lost updates across concurrent tools."""
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    # Open with "a+" to prevent Windows PermissionError on truncation of locked files
    f = open(lock_path, "a+", encoding="utf-8")
    try:
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        f.close()


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            fail_open()
        payload = json.loads(raw)
        conv_id = payload.get("conversationId", "default")
        workspace_paths = payload.get("workspacePaths", [])
        workspace_root = workspace_paths[0] if workspace_paths else os.getcwd()

        memory_dir = os.path.join(workspace_root, ".agents", "memory")
        session_file = os.path.join(memory_dir, ".master_session")

        # Verify caller is master coordinator
        if os.path.exists(session_file):
            try:
                import time
                # Touch heartbeat if called by master
                with open(session_file, "r", encoding="utf-8") as f:
                    master_id = f.read().strip()
                if master_id and master_id != conv_id:
                    # Subagent call: abort without touching master state
                    fail_open()
                # Master call: refresh heartbeat
                os.utime(session_file, None)
            except OSError:
                pass

        ledger_path = os.path.join(memory_dir, "LEDGER.json")
        lock_path = os.path.join(memory_dir, ".ledger.lock")
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Only track and write state if tool is a mutating tool
        if tool_name not in ("write_file", "edit_file"):
            fail_open()

        file_path = tool_args.get("Path")
        if not file_path:
            fail_open()

        abs_file = os.path.abspath(file_path)
        try:
            rel_path = Path(os.path.relpath(abs_file, workspace_root)).as_posix()
        except ValueError:
            # Cross-drive paths on Windows
            rel_path = Path(abs_file).as_posix()

        with file_lock(lock_path):
            ledger_data = {
                "version": 1,
                "rank1_root_intent": {},
                "rank2_active_state": {"current_dag_node": "ACTIVE"},
                "rank3_semantic_ledger": {"modified_files": {}, "decisions": [], "rejected_approaches": []}
            }
            if os.path.exists(ledger_path):
                try:
                    with open(ledger_path, "r", encoding="utf-8") as f:
                        ledger_data = json.load(f)
                except Exception:
                    pass

            files = ledger_data.setdefault("rank3_semantic_ledger", {}).setdefault("modified_files", {})
            # Preserve existing dict entries containing public symbols!
            if isinstance(files.get(rel_path), dict):
                files[rel_path]["status"] = "modified"
            else:
                files[rel_path] = "modified"

            # Atomic write
            os.makedirs(memory_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", dir=memory_dir, delete=False, encoding="utf-8") as tf:
                json.dump(ledger_data, tf, indent=2)
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name

            os.replace(temp_name, ledger_path)
        fail_open()
    except Exception:
        fail_open()


if __name__ == "__main__":
    main()
