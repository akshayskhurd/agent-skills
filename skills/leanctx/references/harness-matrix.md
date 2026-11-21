# Multi-Harness Operational Matrix for `leanctx`

`leanctx` executes across any agent harness through two complementary tiers:
1. **Automated Lifecycle Hooks** (for harnesses with native hook engines, such as Google Antigravity / Gemini CLI).
2. **Universal Directive & CLI Wrappers** (for harnesses driven by prompt skills and tool calls, such as Claude Code, OpenCode, Pi, and Codex).

---

## 1. Harness Execution Architecture

| Harness | Execution Mode | Gating Mechanism | State Ledger Management | Anchor Injection |
| :--- | :--- | :--- | :--- | :--- |
| **Google Antigravity / Gemini CLI** | **Automated Lifecycle Hooks** | `PreToolUse` in `hooks.json` rewrites CLI and clamps `read_file`. | `PostToolUse` atomically writes `LEDGER.json`. Master session isolated. | `PreInvocation` injects micro-anchor into `systemMessage`. |
| **Claude Code** | **Universal Skill & CLI Wrappers** | Wrap commands with `lean_run.py` or native shell piping. Clamp reads with `lean_read.py`. | Maintain `.agents/memory/LEDGER.json` via `ledger_tool.py`. | Micro-anchor preserved in user turns or `CLAUDE.md`. |
| **OpenCode** | **Universal Skill & Tool Wrappers** | Agent routes test/build execution through `lean_run.py`. | CLI calls to `ledger_tool.py set-task`. | Injected into active task prompt. |
| **Pi Agent** | **Universal Skill & Tool Wrappers** | Execute commands via `python3 -m skills.leanctx.scripts.lean_run`. | Read/write `.agents/memory/LEDGER.json`. | Agent anchors each response to active DAG node. |
| **Codex / OpenAI** | **Procedural Skill Directives** | Directives enforce piped execution: `cmd > log; tail -n 25 log`. | State recorded in `LEDGER.json`. | System prompt re-anchoring. |

---

## 2. Universal CLI Command Reference

Across any harness without native hook interception, the agent MUST invoke the following standard CLI utilities bundled in `scripts/`:

### A. Executing High-Volume Commands
Instead of invoking raw, unbounded build/test commands directly:
```bash
# UNIVERSAL COMMAND EXECUTION
python3 skills/leanctx/scripts/lean_run.py "pytest tests/ -v"
python3 skills/leanctx/scripts/lean_run.py "npm test"
python3 skills/leanctx/scripts/lean_run.py "cargo test"
```
* **Behavior**:
  - Raw stdout/stderr streams to `/tmp/leanctx/<id>/last_exec.log` with POSIX mode `0700`.
  - On success ($0$ exit code): Emits tail 25 lines.
  - On failure (non-zero exit code): Emits Head 25 lines (compiler invocation, root exception) AND Tail 25 lines (failure summary).
  - Preserves exact exit code of underlying command.

### B. Safely Reading Large Files
Instead of dumping entire multi-hundred line files into context:
```bash
# UNIVERSAL CLAMPED FILE READING
python3 skills/leanctx/scripts/lean_read.py path/to/large_file.py --start 1 --end 100
python3 skills/leanctx/scripts/lean_read.py path/to/large_file.py --max 120
```
* **Behavior**:
  - Enforces maximum line bounds ($\le 150$ lines default).
  - Emits explicit line range header and truncation notice.

### C. Managing the Living State Ledger
```bash
# Initialize project objective and negative constraints
python3 skills/leanctx/scripts/ledger_tool.py init \
  --goal "Build high-performance caching layer" \
  --constraints "NEVER use external redis; ALWAYS enforce memory cap"

# Advance active DAG milestone
python3 skills/leanctx/scripts/ledger_tool.py set-task \
  --id "TASK-04" \
  --desc "Implement LRU eviction policy"

# Record verified architectural decision
python3 skills/leanctx/scripts/ledger_tool.py add-decision \
  --text "Configured 100ms TTL for cache entries"

# Record modified file
python3 skills/leanctx/scripts/ledger_tool.py add-file \
  --file "src/cache/lru.py" \
  --status "implemented"

# Generate 1-line micro-anchor text
python3 skills/leanctx/scripts/ledger_tool.py anchor
```

---

## 3. Subagent Context Sharding Guidelines

In every harness supporting subagents (Antigravity `invoke_subagent`, Claude Code task agents, OpenCode worker agents):
1. **Offload Exploratory Blast Radius**: Wide codebase searches, multi-file inspections, and exploratory debugging MUST be delegated to subagents.
2. **Ephemeral Context Destruction**: Subagents absorb 50k–100k tokens of Rank 5/6 noise. Upon termination, their context is destroyed.
3. **Semantic Return Only**: Subagents MUST return strictly Rank 2/3 semantic updates ($\le 60$ tokens) to the coordinator.
