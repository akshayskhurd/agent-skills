#!/usr/bin/env python3
"""
Task DAG, Living Perspective State Manager, and Topological Scheduler for Telescope.
Tracks low-level tasks against high-level objectives, resolves dependencies, and renders Mermaid DAGs.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

VALID_STATUSES = [
    "PENDING",
    "IN_PROGRESS",
    "MICRO_EXECUTED",
    "MICRO_GRILLED",
    "COMPLETED",
    "BLOCKED",
]

APPROVED_COMPLETED_STATUSES = {"MICRO_GRILLED", "COMPLETED"}


def load_state(state_file: Path) -> Dict[str, Any]:
    if not state_file.exists():
        print(f"Error: State file '{state_file}' not found. Run `init` first.", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as err:
        print(f"Error loading state from '{state_file}': {err}", file=sys.stderr)
        sys.exit(1)


def save_state(state_file: Path, data: Dict[str, Any]) -> None:
    try:
        state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as err:
        print(f"Error saving state to '{state_file}': {err}", file=sys.stderr)
        sys.exit(1)


def init_perspective(state_file: Path, project: str, objective: str, overwrite: bool = False) -> None:
    if state_file.exists() and not overwrite:
        print(f"Error: Perspective state '{state_file}' already exists. Pass --overwrite to reset.", file=sys.stderr)
        sys.exit(1)

    state = {
        "project": project.strip(),
        "high_level_objective": objective.strip(),
        "architecture_decisions": [],
        "clarifications_needed": [],
        "tasks": [],
    }
    save_state(state_file, state)
    print(f"Initialized perspective state at: {state_file}")


def add_task(
    state_file: Path,
    task_id: str,
    title: str,
    spec: str,
    depends_on: Optional[List[str]] = None,
) -> None:
    state = load_state(state_file)
    task_id_clean = task_id.strip()

    if any(t["id"] == task_id_clean for t in state["tasks"]):
        print(f"Error: Task with ID '{task_id_clean}' already exists.", file=sys.stderr)
        sys.exit(1)

    deps = [d.strip() for raw in (depends_on or []) for d in raw.split(",") if d.strip()]
    existing_ids = {t["id"] for t in state["tasks"]}
    for d in deps:
        if d not in existing_ids:
            print(f"Warning: Dependency '{d}' not yet registered in task DAG.", file=sys.stderr)

    task_entry = {
        "id": task_id_clean,
        "title": title.strip(),
        "spec": spec.strip(),
        "depends_on": deps,
        "status": "PENDING",
        "notes": "",
    }
    state["tasks"].append(task_entry)

    # Detect cycle upon insertion
    cycles = detect_cycles(state["tasks"])
    if cycles:
        print(f"Error: Cycle detected in task DAG: {' -> '.join(cycles)}", file=sys.stderr)
        sys.exit(1)

    save_state(state_file, state)
    print(f"Added task '{task_id_clean}': {title.strip()}")


def update_task(
    state_file: Path,
    task_id: str,
    status: str,
    notes: Optional[str] = None,
) -> None:
    state = load_state(state_file)
    status_clean = status.strip().upper()
    if status_clean not in VALID_STATUSES:
        print(f"Error: Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}", file=sys.stderr)
        sys.exit(1)

    target_task = None
    for t in state["tasks"]:
        if t["id"] == task_id:
            target_task = t
            break

    if not target_task:
        print(f"Error: Task '{task_id}' not found.", file=sys.stderr)
        sys.exit(1)

    target_task["status"] = status_clean
    if notes is not None:
        target_task["notes"] = notes.strip()

    save_state(state_file, state)
    print(f"Updated task '{task_id}' to status '{status_clean}'")


def record_clarification(state_file: Path, question: str, answer: Optional[str] = None) -> None:
    state = load_state(state_file)
    state["clarifications_needed"].append({
        "question": question.strip(),
        "answer": answer.strip() if answer else "",
        "resolved": bool(answer and answer.strip()),
    })
    save_state(state_file, state)
    print(f"Recorded clarification: {question.strip()[:60]}...")


def detect_cycles(tasks: List[Dict[str, Any]]) -> List[str]:
    """Detect cycles in task DAG using depth-first search traversal."""
    graph: Dict[str, List[str]] = {t["id"]: list(t.get("depends_on", [])) for t in tasks}
    visited: Set[str] = set()
    visiting: Set[str] = set()
    cycle_path: List[str] = []

    def dfs(node: str, path: List[str]) -> bool:
        visiting.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            if neighbor in visiting:
                cycle_start_idx = path.index(neighbor)
                cycle_path.extend(path[cycle_start_idx:] + [neighbor])
                return True
            if neighbor not in visited:
                if dfs(neighbor, path):
                    return True
        visiting.remove(node)
        visited.add(node)
        path.pop()
        return False

    for task_id in graph:
        if task_id not in visited:
            if dfs(task_id, []):
                return cycle_path
    return []


def resolve_next_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return all PENDING tasks whose upstream dependencies are verified."""
    task_map = {t["id"]: t for t in tasks}
    ready_tasks = []

    for t in tasks:
        if t["status"] != "PENDING":
            continue
        deps = t.get("depends_on", [])
        deps_satisfied = True
        for dep_id in deps:
            dep_task = task_map.get(dep_id)
            if not dep_task or dep_task["status"] not in APPROVED_COMPLETED_STATUSES:
                deps_satisfied = False
                break
        if deps_satisfied:
            ready_tasks.append(t)

    return ready_tasks


def generate_mermaid_dag(tasks: List[Dict[str, Any]]) -> str:
    """Render a GitHub-compatible color-coded Mermaid flowchart for the task DAG."""
    if not tasks:
        return "```mermaid\nflowchart TD\n    empty[\"No tasks registered\"]\n```"

    lines = [
        "```mermaid",
        "flowchart TD",
        "    %% Status Styling",
        "    classDef completed fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724;",
        "    classDef microgrilled fill:#cce5ff,stroke:#004085,stroke-width:2px,color:#004085;",
        "    classDef inprogress fill:#fff3cd,stroke:#856404,stroke-width:2px,color:#856404;",
        "    classDef pending fill:#e2e3e5,stroke:#383d41,stroke-width:1px,color:#383d41;",
        "    classDef blocked fill:#f8d7da,stroke:#721c24,stroke-width:2px,color:#721c24;",
        "",
    ]

    status_class_map = {
        "COMPLETED": "completed",
        "MICRO_GRILLED": "microgrilled",
        "IN_PROGRESS": "inprogress",
        "PENDING": "pending",
        "BLOCKED": "blocked",
        "MICRO_EXECUTED": "inprogress",
    }

    # Declare nodes with guaranteed alpha-prefixed identifiers and sanitized titles
    for t in tasks:
        node_id = "node_" + re.sub(r"[^a-zA-Z0-9_]", "_", t["id"])
        clean_title = t["title"].replace('"', "'").replace("\n", " ").strip()
        status = t["status"]
        style_class = status_class_map.get(status, "pending")
        lines.append(f'    {node_id}["{t["id"]}: {clean_title} ({status})"]:::{style_class}')

    lines.append("")

    # Declare edges
    edge_count = 0
    for t in tasks:
        dest_node = "node_" + re.sub(r"[^a-zA-Z0-9_]", "_", t["id"])
        for dep_id in t.get("depends_on", []):
            src_node = "node_" + re.sub(r"[^a-zA-Z0-9_]", "_", dep_id)
            lines.append(f"    {src_node} --> {dest_node}")
            edge_count += 1

    if edge_count == 0 and len(tasks) > 1:
        # If no explicit edges exist, arrange sequentially for readable layout
        for i in range(len(tasks) - 1):
            src = "node_" + re.sub(r"[^a-zA-Z0-9_]", "_", tasks[i]["id"])
            dst = "node_" + re.sub(r"[^a-zA-Z0-9_]", "_", tasks[i + 1]["id"])
            lines.append(f"    {src} -.-> {dst}")

    lines.append("```")
    return "\n".join(lines)


def render_perspective_markdown(state_file: Path) -> str:
    state = load_state(state_file)
    tasks = state.get("tasks", [])
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "COMPLETED")
    micro_grilled = sum(1 for t in tasks if t["status"] == "MICRO_GRILLED")
    pct = int(((completed + micro_grilled) / total) * 100) if total > 0 else 0

    lines = [
        f"# Macro Perspective Document: {state.get('project', 'Project')}",
        "",
        "## 1. High-Level Objective",
        state.get("high_level_objective", "Not specified."),
        "",
        f"**Completion**: {completed}/{total} tasks completed ({micro_grilled} micro-grilled, {pct}% ready)",
        "",
        "## 2. Visual Architecture & Dependency DAG",
        generate_mermaid_dag(tasks),
        "",
        "## 3. Low-Level Task Execution Graph",
        "| ID | Title | Dependencies | Status | Notes |",
        "|---|---|---|---|---|",
    ]

    for t in tasks:
        deps = ", ".join(t["depends_on"]) if t["depends_on"] else "None"
        lines.append(f"| `{t['id']}` | {t['title']} | {deps} | `{t['status']}` | {t['notes'] or '-'} |")

    clarifications = state.get("clarifications_needed", [])
    if clarifications:
        lines.extend(["", "## 4. Clarifications & Invariant Resolutions"])
        for idx, c in enumerate(clarifications, start=1):
            status = "RESOLVED" if c["resolved"] else "OPEN"
            lines.append(f"{idx}. **[{status}]** {c['question']}")
            if c["answer"]:
                lines.append(f"   - *Answer*: {c['answer']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Telescope Task DAG, Perspective, and Scheduler")
    parser.add_argument("--file", default=".agents/PERSPECTIVE.json", help="Path to perspective state JSON file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    p_init = subparsers.add_parser("init", help="Initialize a new perspective state file")
    p_init.add_argument("--project", required=True, help="Project name")
    p_init.add_argument("--objective", required=True, help="High-level objective and requirements")
    p_init.add_argument("--overwrite", action="store_true", help="Overwrite existing state")

    # Add Task
    p_add = subparsers.add_parser("add-task", help="Register a low-level task in the DAG")
    p_add.add_argument("--id", required=True, help="Unique task identifier")
    p_add.add_argument("--title", required=True, help="Task title")
    p_add.add_argument("--spec", required=True, help="Specification of input/output contracts")
    p_add.add_argument("--depends-on", nargs="*", help="List of dependent task IDs")

    # Update Task
    p_upd = subparsers.add_parser("update-task", help="Update low-level task status")
    p_upd.add_argument("--id", required=True, help="Task identifier")
    p_upd.add_argument("--status", required=True, choices=VALID_STATUSES, help="New status")
    p_upd.add_argument("--notes", help="Execution or verification notes")

    # Next Task Resolver
    p_next = subparsers.add_parser("next-task", help="Resolve the next ready low-level task in topological order")
    p_next.add_argument("--json", action="store_true", help="Output task payload in JSON format")

    # Clarification
    p_clarify = subparsers.add_parser("clarify", help="Record an open or resolved clarification question")
    p_clarify.add_argument("--question", required=True, help="Clarifying question")
    p_clarify.add_argument("--answer", help="User answer or resolution")

    # Render
    p_render = subparsers.add_parser("render", help="Render living perspective document in Markdown")
    p_render.add_argument("--out", help="Optional output markdown file path")

    # Mermaid
    p_mermaid = subparsers.add_parser("mermaid", help="Output raw Mermaid diagram of task DAG")

    # Status
    p_status = subparsers.add_parser("status", help="Print summary of progress and blockers")

    args = parser.parse_args()
    state_path = Path(args.file).expanduser().resolve()

    if args.command == "init":
        state_path.parent.mkdir(parents=True, exist_ok=True)
        init_perspective(state_path, args.project, args.objective, overwrite=args.overwrite)

    elif args.command == "add-task":
        add_task(state_path, args.id, args.title, args.spec, args.depends_on)

    elif args.command == "update-task":
        update_task(state_path, args.id, args.status, args.notes)

    elif args.command == "next-task":
        state = load_state(state_path)
        tasks = state.get("tasks", [])
        ready = resolve_next_tasks(tasks)
        pending_count = sum(1 for t in tasks if t["status"] == "PENDING")
        in_prog_count = sum(1 for t in tasks if t["status"] in ("IN_PROGRESS", "MICRO_EXECUTED"))
        all_done = (len(tasks) > 0 and pending_count == 0 and in_prog_count == 0)

        if not ready:
            if args.json:
                payload = {
                    "ready": False,
                    "all_completed": all_done,
                    "pending_count": pending_count,
                    "in_progress_count": in_prog_count,
                    "task": None,
                }
                print(json.dumps(payload, indent=2))
            else:
                if all_done:
                    print("All tasks in the DAG are completed.")
                else:
                    print(f"No tasks ready. {pending_count} pending task(s) waiting on upstream dependencies.")
            sys.exit(0)

        next_t = ready[0]
        if args.json:
            payload = {
                "ready": True,
                "all_completed": False,
                "pending_count": pending_count,
                "in_progress_count": in_prog_count,
                "task": next_t,
            }
            print(json.dumps(payload, indent=2))
        else:
            deps_str = ", ".join(next_t.get("depends_on", [])) or "None"
            print("=== NEXT READY TASK ===")
            print(f"ID:          {next_t['id']}")
            print(f"Title:       {next_t['title']}")
            print(f"Depends On:  {deps_str}")
            print(f"Contract:    {next_t['spec']}")

    elif args.command == "clarify":
        record_clarification(state_path, args.question, args.answer)

    elif args.command == "render":
        md = render_perspective_markdown(state_path)
        if args.out:
            out_path = Path(args.out).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            print(f"Rendered perspective document to: {out_path}")
        else:
            print(md)

    elif args.command == "mermaid":
        state = load_state(state_path)
        print(generate_mermaid_dag(state.get("tasks", [])))

    elif args.command == "status":
        state = load_state(state_path)
        tasks = state.get("tasks", [])
        total = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "COMPLETED")
        open_q = sum(1 for c in state.get("clarifications_needed", []) if not c.get("resolved"))
        ready = resolve_next_tasks(tasks)
        print(f"Project: {state.get('project', 'Unknown')}")
        print(f"Progress: {completed}/{total} tasks completed ({(completed/total)*100 if total else 0:.1f}%)")
        print(f"Ready to Execute: {len(ready)} task(s)")
        print(f"Open Clarifications: {open_q}")
        for t in tasks:
            print(f"  [{t['status']}] {t['id']}: {t['title']}")


if __name__ == "__main__":
    main()
