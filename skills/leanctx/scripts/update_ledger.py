#!/usr/bin/env python3
"""
PostToolUse Hook for leanctx.
Atomically updates .agents/memory/LEDGER.json for master session only.
Subagents are strictly locked out of the master ledger.
"""
import sys
import os
import json
import tempfile

def fail_open():
    print(json.dumps({}))
    sys.exit(0)

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

        # Verify caller is master coordinator (allow if session file is missing or older than 2 hours)
        if os.path.exists(session_file):
            try:
                import time
                if time.time() - os.path.getmtime(session_file) <= 7200:
                    with open(session_file, "r", encoding="utf-8") as f:
                        master_id = f.read().strip()
                    if master_id and master_id != conv_id:
                        fail_open()  # Subagent call: abort without touching master state
            except OSError:
                pass

        ledger_path = os.path.join(memory_dir, "LEDGER.json")
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Load existing ledger
        ledger_data = {
            "version": 1,
            "rank1_root_intent": {},
            "rank2_active_state": {"current_dag_node": "ACTIVE"},
            "rank3_semantic_ledger": {"modified_files": {}}
        }
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    ledger_data = json.load(f)
            except Exception:
                pass

        # Only track and write state if tool is a mutating tool
        if tool_name not in ("write_file", "edit_file"):
            fail_open()

        file_path = tool_args.get("Path")
        if not file_path:
            fail_open()

        abs_file = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_file, workspace_root)
        ledger_data.setdefault("rank3_semantic_ledger", {}).setdefault("modified_files", {})[rel_path] = "modified"

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
