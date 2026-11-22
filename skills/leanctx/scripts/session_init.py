#!/usr/bin/env python3
"""
SessionStart Hook for leanctx.
Registers master conversationId, initializes secure scratch directory (mode 0700),
and ensures .gitignore contains .agents/memory/.
"""
import sys
import os
import json

def fail_open():
    print(json.dumps({"injectSteps": []}))
    sys.exit(0)

def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        conv_id = payload.get("conversationId", "default")
        safe_conv_id = "".join(c for c in conv_id if c.isalnum() or c in ("-", "_")) or "default"
        workspace_paths = payload.get("workspacePaths", [])
        workspace_root = workspace_paths[0] if workspace_paths else os.getcwd()

        # 1. Secure scratch directory with 0700 permissions and FIFO log rotation
        scratch_dir = f"/tmp/leanctx/{safe_conv_id}"
        os.makedirs(scratch_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(scratch_dir, 0o700)
        except OSError:
            pass

        # Rolling FIFO cleanup: cap scratch directory to 10 files maximum
        try:
            log_entries = [
                os.path.join(scratch_dir, f) for f in os.listdir(scratch_dir)
                if os.path.isfile(os.path.join(scratch_dir, f))
            ]
            if len(log_entries) > 10:
                log_entries.sort(key=os.path.getmtime)
                for old_file in log_entries[:-10]:
                    try:
                        os.remove(old_file)
                    except OSError:
                        pass
        except OSError:
            pass

        # 2. Register master session ID (refresh if missing or older than 2 hours)
        memory_dir = os.path.join(workspace_root, ".agents", "memory")
        os.makedirs(memory_dir, exist_ok=True)
        session_file = os.path.join(memory_dir, ".master_session")
        is_stale = False
        if os.path.exists(session_file):
            try:
                import time
                if time.time() - os.path.getmtime(session_file) > 7200:
                    is_stale = True
            except OSError:
                is_stale = True

        if not os.path.exists(session_file) or is_stale:
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
