#!/usr/bin/env python3
"""
SessionStart Hook for leanctx.
Registers master conversationId, initializes secure UID-scoped scratch directory (mode 0700),
and ensures .gitignore contains .agents/memory/.
"""
import json
import os
import sys
import tempfile
import time


def fail_open():
    print(json.dumps({"injectSteps": []}))
    sys.exit(0)


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


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        conv_id = payload.get("conversationId", "default")
        safe_conv_id = "".join(c for c in conv_id if c.isalnum() or c in ("-", "_")) or "default"
        workspace_paths = payload.get("workspacePaths", [])
        workspace_root = workspace_paths[0] if workspace_paths else os.getcwd()

        # 1. Secure scratch directory with 0700 permissions
        scratch_dir = get_scratch_dir(safe_conv_id)

        # 2. Register master session ID (prevent subagent lockout)
        memory_dir = os.path.join(workspace_root, ".agents", "memory")
        os.makedirs(memory_dir, exist_ok=True)
        session_file = os.path.join(memory_dir, ".master_session")

        can_register = True
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    existing_master = f.read().strip()
                # If caller is the existing master, refresh heartbeat
                if existing_master == conv_id:
                    os.utime(session_file, None)
                    can_register = False
                elif time.time() - os.path.getmtime(session_file) <= 7200:
                    # Active session exists; do NOT let a new/subagent conversation overwrite master
                    can_register = False
            except OSError:
                pass

        if can_register:
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(conv_id)

        # 3. Ensure .gitignore hygiene
        gitignore_path = os.path.join(workspace_root, ".gitignore")
        ignore_entry = ".agents/memory/\n"
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if ".agents/memory/" not in content:
                    with open(gitignore_path, "a", encoding="utf-8") as f:
                        f.write(f"\n# leanctx working memory\n{ignore_entry}")
            except OSError:
                pass

        fail_open()
    except Exception:
        fail_open()


if __name__ == "__main__":
    main()
