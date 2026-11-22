# Multi-Harness Operational Matrix for `leanctx`

`leanctx` executes across any agent harness through two complementary tiers:
1. **Automated Lifecycle Hooks** (for harnesses with native hook engines, such as Google Antigravity / Gemini CLI).
2. **Universal Directives & CLI Wrappers** (for harnesses driven by prompt skills and tool calls, such as Claude Code, OpenCode, Pi, and Codex).

---

## 1. Dynamic Script Path Resolution

Agent harnesses install skills in different locations. The agent MUST resolve the `leanctx` script root dynamically:

1. **Check Local Workspace**: `.agents/skills/leanctx/scripts/` or `skills/leanctx/scripts/`
2. **Check Global Harness Directory**:
   - Claude Code: `~/.claude/skills/leanctx/scripts/`
   - Google Antigravity / Gemini CLI: `~/.gemini/config/skills/leanctx/scripts/`
   - Codex / OpenAI: `~/.codex/skills/leanctx/scripts/`
   - OpenCode: `~/.opencode/skills/leanctx/scripts/`
   - Pi Agent: `~/.pi/skills/leanctx/scripts/`
3. **Environment Override**: Check `LEANCTX_DIR` environment variable.

Define `<SCRIPTS>` as the resolved directory. Invoke utilities as:
```bash
python3 "<SCRIPTS>/lean_run.py" "<command>"
python3 "<SCRIPTS>/lean_read.py" "<file>"
python3 "<SCRIPTS>/ledger_tool.py" "<subcommand>"
```
On Windows systems without `python3`, substitute `python`.

---

## 2. Harness Execution Architecture

| Harness | Execution Mode | Gating Mechanism | State Ledger Management | Anchor / Recovery |
| :--- | :--- | :--- | :--- | :--- |
| **Google Antigravity / Gemini CLI** | **Automated Lifecycle Hooks** | `PreToolUse` in `hooks.json` rewrites high-volume CLI and clamps `read_file`. | `PostToolUse` atomically writes `LEDGER.json`. Master session isolated. | `PreInvocation` injects micro-anchor into `systemMessage`. |
| **Claude Code** | **Universal Skill & CLI Wrappers** | Wrap build/test commands via `lean_run.py`. Clamp reads via `lean_read.py`. | Maintain `.agents/memory/LEDGER.json` via `ledger_tool.py`. | Anchor in prompt. Run `ledger_tool.py rehydrate` post-compaction. |
| **OpenCode** | **Universal Skill & Tool Wrappers** | Route test/build commands through `lean_run.py`. | CLI calls to `ledger_tool.py set-task`. | Anchor in task state. Re-hydrate post-compaction. |
| **Pi Agent** | **Universal Skill & Tool Wrappers** | Execute commands via `lean_run.py`. | Read/write `.agents/memory/LEDGER.json`. | Maintain anchor in prompt turns. |
| **Codex / OpenAI** | **Procedural Skill Directives** | Directives enforce piped execution: `cmd > log; tail -n 25 log`. | State recorded in `LEDGER.json`. | Re-hydrate via `ledger_tool.py rehydrate`. |

---

## 3. Universal CLI Command Reference

### A. Executing High-Volume Commands
Instead of invoking raw, unbounded build/test commands directly:
```bash
# UNIVERSAL COMMAND EXECUTION
python3 "<SCRIPTS>/lean_run.py" "pytest tests/ -v"
python3 "<SCRIPTS>/lean_run.py" "npm test"
python3 "<SCRIPTS>/lean_run.py" "cargo test"
```
* **Behavior**:
  - Raw stdout/stderr streams to `/tmp/leanctx/<id>/last_exec.log`.
  - On success ($0$ exit code): Emits tail 25 lines.
  - On failure (non-zero exit code): Emits Head 15 lines, the root-cause error cluster from the middle of the log, and Tail 15 lines.
  - Preserves exact exit code of underlying command with 300s timeout guard.

### B. Drilling Down into Full Logs on Command Failure
When the diagnostic summary misses specific error lines or you need full stack traces:
```bash
# Search for specific error signatures
grep -n -C 5 -i -E "error|fail|panic|exception|traceback" /tmp/leanctx/<id>/last_exec.log

# Read targeted line slice around the error
python3 "<SCRIPTS>/lean_read.py" /tmp/leanctx/<id>/last_exec.log --start 180 --end 240
```

### C. Safely Reading Large Files
Instead of dumping entire multi-hundred line files into context:
```bash
# UNIVERSAL CLAMPED FILE READING
python3 "<SCRIPTS>/lean_read.py" path/to/large_file.py --start 1 --end 100
python3 "<SCRIPTS>/lean_read.py" path/to/large_file.py --max 150
```

### D. Managing the Living State Ledger
```bash
# Initialize project objective and negative constraints
python3 "<SCRIPTS>/ledger_tool.py" init \
  --goal "Build high-performance caching layer" \
  --constraints "NEVER use external redis; ALWAYS enforce memory cap"

# Advance active DAG milestone
python3 "<SCRIPTS>/ledger_tool.py" set-task \
  --id "TASK-04" \
  --desc "Implement LRU eviction policy"

# Record verified architectural decision
python3 "<SCRIPTS>/ledger_tool.py" add-decision \
  --text "Configured 100ms TTL for cache entries"

# Record modified file
python3 "<SCRIPTS>/ledger_tool.py" add-file \
  --file "src/cache/lru.py" \
  --status "implemented"

# Generate 1-line micro-anchor text
python3 "<SCRIPTS>/ledger_tool.py" anchor

# Post-compaction / resumption re-hydration
python3 "<SCRIPTS>/ledger_tool.py" rehydrate
```

---

## 4. Subagent Context Sharding Guidelines

### Across Harnesses Supporting Subagents
- **Antigravity**: Launch via `invoke_subagent`.
- **Claude Code**: Launch via Task subagent tool.
- **OpenCode**: Launch via worker subagent or child agent process.

### Fallback for Harnesses Without Subagents (Codex / Single-Agent Mode)
When running in an environment without subagent delegation:
1. Run discovery and exploratory scans via targeted one-liners piping directly to `grep` or temporary scratch files.
2. Extract only matching file names and line numbers.
3. NEVER dump full raw directory trees or unindexed files into the conversational prompt.
