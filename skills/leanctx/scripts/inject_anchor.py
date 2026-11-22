#!/usr/bin/env python3
"""
PreInvocation Hook for leanctx.
Injects a single-line micro-anchor (<= 60 tokens) in exact protojson schema.
Prevents quadratic token inflation across turns.
"""
import sys
import os
import json

def emit(inject_steps=None):
    print(json.dumps({"injectSteps": inject_steps or []}))
    sys.exit(0)

def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        cwd = payload.get("cwd", os.getcwd())
        ledger_path = os.path.join(cwd, ".agents", "memory", "LEDGER.json")

        if not os.path.exists(ledger_path):
            emit()

        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        goal = ledger.get("rank1_root_intent", {}).get("goal", "Execute active tasks")
        constraints = ledger.get("rank1_root_intent", {}).get("constraints", [])
        constraints_str = "; ".join(constraints) if constraints else "None"
        active = ledger.get("rank2_active_state", {}).get("current_dag_node", "INITIALIZE")

        # Bounded micro-anchor: <= 60 tokens
        anchor_text = f"[leanctx-anchor] GOAL: {goal} | CONSTRAINTS: {constraints_str} | ACTIVE: {active} | STATE: .agents/memory/LEDGER.json"

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
