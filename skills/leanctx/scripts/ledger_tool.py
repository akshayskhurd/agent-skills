#!/usr/bin/env python3
"""
Universal Living State Ledger Manager for leanctx across any harness.
Provides atomic initialization, updates, and micro-anchor generation for .agents/memory/LEDGER.json.
Enforces advisory file locking, path normalization, and token budget ceilings.
"""
import argparse
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any


def get_ledger_path(workspace_root: str = None, session_id: str = None) -> str:
    root = workspace_root if workspace_root else os.getcwd()
    if session_id:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"
        return os.path.join(root, ".agents", "memory", f"LEDGER_{safe_id}.json")
    return os.path.join(root, ".agents", "memory", "LEDGER.json")


def get_lock_path(ledger_path: str) -> str:
    return os.path.join(os.path.dirname(ledger_path), ".ledger.lock")


@contextlib.contextmanager
def file_lock(lock_path: str):
    """Cross-platform advisory file lock for atomic read-modify-write transactions."""
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    f = open(lock_path, "w", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
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


def touch_heartbeat(workspace_root: str = None):
    """Refresh master session mtime to prevent stale subagent takeover."""
    root = workspace_root if workspace_root else os.getcwd()
    session_file = os.path.join(root, ".agents", "memory", ".master_session")
    if os.path.exists(session_file):
        try:
            os.utime(session_file, None)
        except OSError:
            pass


def load_ledger(ledger_path: str) -> Dict[str, Any]:
    default_ledger = {
        "version": 1,
        "rank1_root_intent": {"goal": "", "constraints": [], "version": 1, "amendment_history": []},
        "rank2_active_state": {"current_dag_node": "INITIALIZE", "description": ""},
        "rank3_semantic_ledger": {"modified_files": {}, "decisions": [], "rejected_approaches": []}
    }
    if not os.path.exists(ledger_path):
        return default_ledger
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("version", 1)
            data.setdefault("rank1_root_intent", {}).setdefault("goal", "")
            data.setdefault("rank1_root_intent", {}).setdefault("constraints", [])
            data.setdefault("rank2_active_state", {}).setdefault("current_dag_node", "INITIALIZE")
            data.setdefault("rank3_semantic_ledger", {}).setdefault("modified_files", {})
            data.setdefault("rank3_semantic_ledger", {}).setdefault("decisions", [])
            data.setdefault("rank3_semantic_ledger", {}).setdefault("rejected_approaches", [])
            return data
    except Exception:
        return default_ledger


def save_ledger_atomic(ledger_path: str, data: Dict[str, Any]) -> None:
    dir_name = os.path.dirname(ledger_path)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        temp_name = tf.name
    os.replace(temp_name, ledger_path)


def truncate_text(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars - 3] + "..."


def cmd_init(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    with file_lock(lock_file):
        data = load_ledger(path)
        data["rank1_root_intent"]["goal"] = truncate_text(args.goal, 400)
        if args.constraints:
            data["rank1_root_intent"]["constraints"] = [
                truncate_text(c.strip(), 150) for c in args.constraints.split(";") if c.strip()
            ][:10]
        data["rank1_root_intent"]["version"] = 1
        data["rank1_root_intent"]["amendment_history"] = []
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Initialized leanctx ledger at: {path}")


def cmd_amend_intent(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    with file_lock(lock_file):
        data = load_ledger(path)
        root = data.setdefault("rank1_root_intent", {})
        history = root.setdefault("amendment_history", [])
        prev_goal = root.get("goal", "")
        prev_constraints = list(root.get("constraints", []))

        if args.goal:
            root["goal"] = truncate_text(args.goal, 400)
        if args.constraints is not None:
            root["constraints"] = [
                truncate_text(c.strip(), 150) for c in args.constraints.split(";") if c.strip()
            ][:10]

        history.append({
            "timestamp": int(time.time()),
            "reason": truncate_text(args.reason, 200),
            "previous_goal": prev_goal,
            "previous_constraints": prev_constraints
        })
        # Bound history to last 5 amendments to prevent unbounded ledger growth
        root["amendment_history"] = history[-5:]
        root["version"] = root.get("version", 1) + 1
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Amended root intent (version {root['version']}) per user authorization: {args.reason}")


def cmd_set_task(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    with file_lock(lock_file):
        data = load_ledger(path)
        data["rank2_active_state"]["current_dag_node"] = truncate_text(args.id, 50)
        if args.desc:
            data["rank2_active_state"]["description"] = truncate_text(args.desc, 300)
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Active task updated to [{args.id}]: {args.desc or ''}")


def cmd_add_decision(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    with file_lock(lock_file):
        data = load_ledger(path)
        decisions = data.setdefault("rank3_semantic_ledger", {}).setdefault("decisions", [])
        decisions.append(truncate_text(args.text, 250))
        # Keep most recent 30 decisions (within 1,500 token budget)
        data["rank3_semantic_ledger"]["decisions"] = decisions[-30:]
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Added decision to ledger: {args.text}")


def cmd_add_rejection(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    with file_lock(lock_file):
        data = load_ledger(path)
        rejections = data.setdefault("rank3_semantic_ledger", {}).setdefault("rejected_approaches", [])
        entry = f"{truncate_text(args.approach, 120)} -> REJECTED: {truncate_text(args.reason, 150)}"
        rejections.append(entry)
        # Keep most recent 20 rejections to avoid bloat
        data["rank3_semantic_ledger"]["rejected_approaches"] = rejections[-20:]
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Recorded rejected approach: {entry}")


def cmd_add_file(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    lock_file = get_lock_path(path)
    norm_file = Path(args.file).as_posix()
    with file_lock(lock_file):
        data = load_ledger(path)
        files = data.setdefault("rank3_semantic_ledger", {}).setdefault("modified_files", {})
        if getattr(args, "symbols", None):
            symbols_list = [truncate_text(s.strip(), 120) for s in args.symbols.split(";") if s.strip()][:10]
            files[norm_file] = {"status": args.status, "symbols": symbols_list}
        elif isinstance(files.get(norm_file), dict):
            files[norm_file]["status"] = args.status
        else:
            files[norm_file] = args.status
        save_ledger_atomic(path, data)
    touch_heartbeat(args.workspace)
    print(f"Recorded file state: {norm_file} -> {args.status}")


def cmd_show(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    if not os.path.exists(path):
        print(f"No ledger found at: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        print(f.read())


def cmd_rehydrate(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    if not os.path.exists(path):
        print(f"[leanctx-rehydrate] No active state ledger found at: {path}")
        return
    data = load_ledger(path)
    goal = data.get("rank1_root_intent", {}).get("goal", "Execute plan")
    constraints = data.get("rank1_root_intent", {}).get("constraints", [])
    active = data.get("rank2_active_state", {}).get("current_dag_node", "INITIALIZE")
    desc = data.get("rank2_active_state", {}).get("description", "")
    decisions = data.get("rank3_semantic_ledger", {}).get("decisions", [])
    rejections = data.get("rank3_semantic_ledger", {}).get("rejected_approaches", [])
    files = data.get("rank3_semantic_ledger", {}).get("modified_files", {})

    print("=" * 60)
    print("🔄 [leanctx-rehydrate] SESSION CONTEXT RESTORED FROM LEDGER")
    print(f"• ROOT INTENT: {goal}")
    if constraints:
        print(f"• NON-NEGOTIABLE CONSTRAINTS: {'; '.join(constraints)}")
    print(f"• ACTIVE TASK: [{active}] {desc}")
    if decisions:
        print(f"• VERIFIED DECISIONS ({len(decisions)}):")
        for d in decisions[-5:]:
            print(f"  - {d}")
    if rejections:
        print(f"• DEAD ENDS / REJECTED APPROACHES ({len(rejections)}):")
        for r in rejections[-5:]:
            print(f"  - ⛔ {r}")
    if files:
        recent_files = list(files.items())[-8:]
        print(f"• RECENT TOUCHED FILES & PUBLIC SIGNATURES ({len(files)} total, showing last {len(recent_files)}):")
        for f_path, meta in recent_files:
            if isinstance(meta, dict) and meta.get("symbols"):
                syms = ", ".join(meta["symbols"])
                print(f"  - {f_path}: {syms}")
            elif isinstance(meta, dict):
                print(f"  - {f_path} ({meta.get('status', 'modified')})")
            else:
                print(f"  - {f_path} ({meta})")
    print("=" * 60)


def cmd_status(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    if not os.path.exists(path):
        print(f"Status: Inactive (no ledger at {path})")
        return
    data = load_ledger(path)
    files_count = len(data.get("rank3_semantic_ledger", {}).get("modified_files", {}))
    decisions_count = len(data.get("rank3_semantic_ledger", {}).get("decisions", []))
    rejections_count = len(data.get("rank3_semantic_ledger", {}).get("rejected_approaches", []))
    print(f"Status: Active | Files Tracked: {files_count} | Decisions: {decisions_count} | Dead Ends: {rejections_count} | Path: {path}")


def cmd_anchor(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    goal = truncate_text(data.get("rank1_root_intent", {}).get("goal", "Execute plan"), 60)
    constraints = data.get("rank1_root_intent", {}).get("constraints", [])
    constraints_str = truncate_text("; ".join(constraints), 70) if constraints else "None"
    active = truncate_text(data.get("rank2_active_state", {}).get("current_dag_node", "INITIALIZE"), 25)
    desc = truncate_text(data.get("rank2_active_state", {}).get("description", ""), 45)
    ledger_file = os.path.basename(path)
    anchor = f"[leanctx-anchor] GOAL: {goal} | CONSTRAINTS: {constraints_str} | ACTIVE: {active} ({desc}) | STATE: {ledger_file}"
    # Strictly enforce <= 240 chars (~60 tokens)
    if len(anchor) > 240:
        anchor = anchor[:237] + "..."
    print(anchor)


def main():
    parser = argparse.ArgumentParser(description="Universal leanctx Living State Ledger CLI")
    parser.add_argument("--workspace", "-w", default=None, help="Workspace root directory (defaults to cwd)")
    parser.add_argument("--session", "-s", default=None, help="Optional session ID for parallel/subagent state isolation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init", help="Initialize or update root intent")
    init_p.add_argument("--goal", "-g", required=True, help="Root goal / acceptance objective")
    init_p.add_argument("--constraints", "-c", help="Semicolon-separated negative constraints")
    init_p.set_defaults(func=cmd_init)

    amend_p = subparsers.add_parser("amend-intent", help="Amend root intent or constraints per explicit user authorization")
    amend_p.add_argument("--goal", "-g", help="Updated user goal")
    amend_p.add_argument("--constraints", "-c", help="Updated semicolon-separated constraints")
    amend_p.add_argument("--reason", "-r", required=True, help="Explicit user instruction prompting amendment")
    amend_p.set_defaults(func=cmd_amend_intent)

    task_p = subparsers.add_parser("set-task", help="Set active task in DAG")
    task_p.add_argument("--id", required=True, help="Task ID or milestone name")
    task_p.add_argument("--desc", help="Short description of task")
    task_p.set_defaults(func=cmd_set_task)

    dec_p = subparsers.add_parser("add-decision", help="Record verified technical decision")
    dec_p.add_argument("--text", "-t", required=True, help="Decision description")
    dec_p.set_defaults(func=cmd_add_decision)

    rej_p = subparsers.add_parser("add-rejection", help="Record failed path / dead-end approach to prevent repeat attempts")
    rej_p.add_argument("--approach", "-a", required=True, help="Description of attempted approach")
    rej_p.add_argument("--reason", "-r", required=True, help="Why approach failed or was rejected")
    rej_p.set_defaults(func=cmd_add_rejection)

    file_p = subparsers.add_parser("add-file", help="Record modified file in ledger")
    file_p.add_argument("--file", "-f", required=True, help="File path relative to workspace")
    file_p.add_argument("--status", default="modified", help="Status description")
    file_p.add_argument("--symbols", "-s", help="Public exported symbols/signatures (semicolon-separated)")
    file_p.set_defaults(func=cmd_add_file)

    show_p = subparsers.add_parser("show", help="Display current ledger contents")
    show_p.set_defaults(func=cmd_show)

    anc_p = subparsers.add_parser("anchor", help="Generate single-line micro-anchor text")
    anc_p.set_defaults(func=cmd_anchor)

    rehyd_p = subparsers.add_parser("rehydrate", help="Restore full context after compaction or resumption")
    rehyd_p.set_defaults(func=cmd_rehydrate)

    stat_p = subparsers.add_parser("status", help="Display summary status of active ledger")
    stat_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
