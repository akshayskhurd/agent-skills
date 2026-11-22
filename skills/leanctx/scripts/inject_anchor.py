#!/usr/bin/env python3
"""
PreInvocation Hook for leanctx.
Injects a single-line micro-anchor (<= 60 tokens, <= 240 chars) in exact protojson schema.
Supports session-isolated subagent anchors and prevents token inflation across turns.
"""
import json
import os
import sys


def emit(inject_steps=None):
    print(json.dumps({"injectSteps": inject_steps or []}))
    sys.exit(0)


def truncate_text(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars - 3] + "..."


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        cwd = payload.get("cwd", os.getcwd())
        session_id = payload.get("sessionId") or payload.get("session")

        ledger_file = f"LEDGER_{session_id}.json" if session_id else "LEDGER.json"
        ledger_path = os.path.join(cwd, ".agents", "memory", ledger_file)

        if not os.path.exists(ledger_path):
            emit()

        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        goal = truncate_text(ledger.get("rank1_root_intent", {}).get("goal", "Execute active tasks"), 60)
        constraints = ledger.get("rank1_root_intent", {}).get("constraints", [])
        constraints_str = truncate_text("; ".join(constraints), 70) if constraints else "None"
        active = truncate_text(ledger.get("rank2_active_state", {}).get("current_dag_node", "INITIALIZE"), 25)

        # Bounded micro-anchor: strictly <= 240 chars (~60 tokens)
        anchor_text = f"[leanctx-anchor] GOAL: {goal} | CONSTRAINTS: {constraints_str} | ACTIVE: {active} | STATE: .agents/memory/{ledger_file}"
        if len(anchor_text) > 240:
            anchor_text = anchor_text[:237] + "..."

        step = {
            "systemMessage": {
                "systemMessage": anchor_text
            }
        }
        emit([step])
    except Exception:
        emit()


if __name__ == "__main__":
    main()
