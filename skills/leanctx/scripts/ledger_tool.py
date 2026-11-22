#!/usr/bin/env python3
"""
Universal Living State Ledger Manager for leanctx across any harness.
Provides atomic initialization, updates, and micro-anchor generation for .agents/memory/LEDGER.json.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from typing import Dict, Any


def get_ledger_path(workspace_root: str = None, session_id: str = None) -> str:
    root = workspace_root if workspace_root else os.getcwd()
    if session_id:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"
        return os.path.join(root, ".agents", "memory", f"LEDGER_{safe_id}.json")
    return os.path.join(root, ".agents", "memory", "LEDGER.json")


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


def cmd_init(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    data["rank1_root_intent"]["goal"] = args.goal
    if args.constraints:
        data["rank1_root_intent"]["constraints"] = [c.strip() for c in args.constraints.split(";") if c.strip()]
    data["rank1_root_intent"]["version"] = 1
    data["rank1_root_intent"]["amendment_history"] = []
    save_ledger_atomic(path, data)
    print(f"Initialized leanctx ledger at: {path}")


def cmd_amend_intent(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    root = data.setdefault("rank1_root_intent", {})
    history = root.setdefault("amendment_history", [])
    prev_goal = root.get("goal", "")
    prev_constraints = list(root.get("constraints", []))

    if args.goal:
        root["goal"] = args.goal
    if args.constraints is not None:
        root["constraints"] = [c.strip() for c in args.constraints.split(";") if c.strip()]

    history.append({
        "timestamp": int(time.time()),
        "reason": args.reason,
        "previous_goal": prev_goal,
        "previous_constraints": prev_constraints
    })
    root["version"] = root.get("version", 1) + 1
    save_ledger_atomic(path, data)
    print(f"Amended root intent (version {root['version']}) per user authorization: {args.reason}")


def cmd_set_task(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    data["rank2_active_state"]["current_dag_node"] = args.id
    if args.desc:
        data["rank2_active_state"]["description"] = args.desc
    save_ledger_atomic(path, data)
    print(f"Active task updated to [{args.id}]: {args.desc or ''}")


def cmd_add_decision(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    decisions = data.setdefault("rank3_semantic_ledger", {}).setdefault("decisions", [])
    decisions.append(args.text)
    save_ledger_atomic(path, data)
    print(f"Added decision to ledger: {args.text}")


def cmd_add_rejection(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    rejections = data.setdefault("rank3_semantic_ledger", {}).setdefault("rejected_approaches", [])
    entry = f"{args.approach} -> REJECTED: {args.reason}"
    rejections.append(entry)
    save_ledger_atomic(path, data)
    print(f"Recorded rejected approach: {entry}")


def cmd_add_file(args):
    path = get_ledger_path(args.workspace, getattr(args, "session", None))
    data = load_ledger(path)
    files = data.setdefault("rank3_semantic_ledger", {}).setdefault("modified_files", {})
    if getattr(args, "symbols", None):
        symbols_list = [s.strip() for s in args.symbols.split(";") if s.strip()]
        files[args.file] = {"status": args.status, "symbols": symbols_list}
    else:
        files[args.file] = args.status
    save_ledger_atomic(path, data)
    print(f"Recorded file state: {args.file} -> {args.status}")


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
        print(f"• TOUCHED FILES & PUBLIC SIGNATURES ({len(files)}):")
        for f_path, meta in list(files.items())[:8]:
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
    goal = data.get("rank1_root_intent", {}).get("goal", "Execute plan")
    constraints = data.get("rank1_root_intent", {}).get("constraints", [])
    constraints_str = "; ".join(constraints) if constraints else "None"
    active = data.get("rank2_active_state", {}).get("current_dag_node", "INITIALIZE")
    desc = data.get("rank2_active_state", {}).get("description", "")
    ledger_file = os.path.basename(path)
    anchor = f"[leanctx-anchor] GOAL: {goal} | CONSTRAINTS: {constraints_str} | ACTIVE: {active} ({desc}) | STATE: {ledger_file}"
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
