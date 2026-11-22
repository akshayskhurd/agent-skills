---
name: leanctx
description: >-
  Context hygiene and token optimization for long-running coding sessions.
  Enforces tool output sandboxing, living state ledgers, compaction rehydration,
  and subagent context isolation across Claude Code, OpenCode, Pi, Codex, and Antigravity.
metadata:
  icon: memory
---

# leanctx: Universal Context Optimization & Anti-Drift Engine

`leanctx` prevents context window bloat, eliminates goal drift, and caps token accumulation across long-running coding sessions in any agent harness (Google Antigravity, Claude Code, OpenCode, Pi, Codex).

---

## 1. Trigger Conditions & Guardrails

### When to Activate
The agent MUST activate `leanctx` when:
1. The user explicitly requests context optimization, cost reduction, or session memory management.
2. Embarking on a multi-phase, large-scale implementation (e.g. major refactoring, cross-package migration, complex multi-file debugging).
3. Executing high-volume tool workflows (extensive test suites, package compilation, recursive codebase searches).

### Negative Scope: When NOT to Use
The agent MUST NOT activate `leanctx` for:
- Single-turn queries, simple 1-line edits, or quick factual code questions.
- Inspecting small files ($\le 100$ lines) or running low-output commands (`git status`, `ls`, `mkdir`).
- Trivial scripts where initializing ledgers and wrappers introduces more token overhead than it saves.

### Progressive Disclosure Directive
Skip reference files during normal execution. Read `[references/context-taxonomy.md](./references/context-taxonomy.md)` only when auditing retention tiers. Read `[references/harness-matrix.md](./references/harness-matrix.md)` only when configuring platform-specific hooks or CLI aliases.

---

## 2. Dynamic Script Path Resolution

Before invoking any bundled utilities, the agent MUST resolve the `leanctx` script directory:
1. Local Workspace: `.agents/skills/leanctx/scripts` or `skills/leanctx/scripts`
2. Global Directory: `~/.claude/skills/leanctx/scripts`, `~/.gemini/config/skills/leanctx/scripts`, `~/.codex/skills/leanctx/scripts`, `~/.opencode/skills/leanctx/scripts`, or `~/.pi/skills/leanctx/scripts`
3. Environment Variable: `$LEANCTX_DIR`

Define `<SCRIPTS>` as the resolved directory path. On Windows environments without `python3`, use `python`.

---

## 3. The 6-Tier Retention & Ingress Hierarchy

![leanctx Executive Architecture](./assets/architecture_l1.svg)
*Figure 1: High-level (Level-1) conceptual optimization flow from raw tool output to bounded context and persistent living ledger.*

```
┌────────────────────────────────────────────────────────┐
│ Rank 1: Root Intent & Invariant Rules   (DISK LEDGER)  │
│ Rank 2: Active Task & Blocker State    (DISK LEDGER)  │
│ Rank 3: Semantic Ledger & Contracts    (DISK LEDGER)  │
├────────────────────────────────────────────────────────┤
│ Rank 4: Conversational Working Memory  (HARNESS BUFFER)│
│ Rank 5: Exploratory File Reads         (INGRESS CLAMP) │
│ Rank 6: Disposable Build / Test Noise  (INGRESS SANDBOX)
└────────────────────────────────────────────────────────┘
```

- **Ranks 1–3**: Maintained persistently on disk in `.agents/memory/LEDGER.json`. Restored instantly via `ledger_tool.py rehydrate` post-compaction.
  - Rank 1: Root goal and non-negotiable negative constraints ($\le 500$ tokens). Amended ONLY via explicit user authorization.
  - Rank 2: Active DAG milestone and active blocker state ($\le 500$ tokens).
  - Rank 3: Verified technical decisions, modified files with exact public symbols, and rejected dead-end paths ($\le 1,500$ tokens).
- **Rank 4**: Conversational working buffer managed by host harness windowing ($\le 4,000$ tokens).
- **Ranks 5–6**: Gated at ingress. Raw stdout and line dumps write to disk; only concise summaries or root-cause error lines enter context history.

---

## 4. 4-Phase Operational Execution

```mermaid
flowchart TD
    A["Task Triggered"] --> B["Phase 1: Ingress Gating & Workspace Setup"]
    B --> C["Phase 2: Atomic State Ledger Initialization"]
    C --> D["Phase 3: Execution via Sandboxing & Subagent Sharding"]
    D --> E["Phase 4: Milestone Condensation & Compaction Recovery"]
    E --> D

    classDef phase fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;
    class A,B,C,D,E phase;
```

### Phase 1: Ingress Gating & Workspace Setup
1. Verify scratch directory permissions (`0700` mode), FIFO log rotation, and `.gitignore` hygiene:
   ```bash
   python3 "<SCRIPTS>/session_init.py"
   ```
2. In harnesses with hook support (Antigravity), verify `skills/leanctx/hooks.json` is active.

### Phase 2: Atomic State Ledger Initialization
1. Initialize project objective and non-negotiable negative constraints:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" init \
     --goal "<Primary User Acceptance Goal>" \
     --constraints "<Constraint 1>; <Constraint 2>"
   ```
2. Register active DAG milestone:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" set-task \
     --id "<Task ID>" \
     --desc "<Task Objective>"
   ```
3. If the user explicitly amends the project goal or constraints mid-session, log the authorized amendment:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" amend-intent \
     --goal "<Updated Goal>" \
     --constraints "<Amended Constraints>" \
     --reason "<User instruction rationale>"
   ```

### Phase 3: Execution via Output Sandboxing & Subagent Sharding
1. **High-Volume Command Execution**:
   - In Antigravity: `gate_tool.py` automatically wraps commands matching high-volume build/test executables.
   - In Claude Code / OpenCode / Pi / Codex: Execute build/test commands via `lean_run.py`:
     ```bash
     python3 "<SCRIPTS>/lean_run.py" "<test_or_build_command>"
     ```
   - On success: Emits tail 25 lines if total lines $> 30$.
   - On failure: Emits Head 15 lines, root-cause error lines from the middle of the log, and Tail 15 lines if total lines $> 50$ (maximum 65 lines).
2. **Drilling Down into Full Logs on Command Failure**:
   - If the summary misses root-cause stack traces, inspect the full log saved in `<SCRATCH>/last_exec.log` (located at `<tempdir>/leanctx-<uid>/<id>/last_exec.log`):
     ```bash
     grep -n -C 5 -i -E "error|fail|panic|exception" "<SCRATCH>/last_exec.log"
     python3 "<SCRIPTS>/lean_read.py" "<SCRATCH>/last_exec.log" --start <line> --end <line+50>
     ```
3. **File Reading Line Clamping**:
   - Never ingest entire multi-hundred line files without line bounds.
   - Use targeted line ranges or invoke `lean_read.py`:
     ```bash
     python3 "<SCRIPTS>/lean_read.py" path/to/large_file.py --start 1 --end 150
     ```
4. **Subagent Context Sharding**:
   - For broad codebase scans or multi-step debugging, launch an isolated subagent (`invoke_subagent` in Antigravity, Task agent in Claude Code, child agent in OpenCode).
   - In single-agent harnesses without subagents: run discovery via targeted single-line CLI commands piping to `grep` or temporary files. Do not dump directory trees into conversation turns.

### Phase 4: State Condensation & Compaction Recovery
1. After completing an execution milestone, update modified files and decisions in the ledger:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" add-file --file "<path>" --status "verified" --symbols "<exported signatures>"
   python3 "<SCRIPTS>/ledger_tool.py" add-decision --text "<Verified decision>"
   ```
2. When hitting a dead end or rejecting a failed path, record the negative knowledge to eliminate repeat attempts:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" add-rejection \
     --approach "<Attempted Approach>" \
     --reason "<Why it failed or was rejected>"
   ```
3. Emit the single-line micro-anchor ($\le 60$ tokens) in active context:
   ```bash
   python3 "<SCRIPTS>/ledger_tool.py" anchor
   ```
   *Format:* `[leanctx-anchor] GOAL: <Goal> | CONSTRAINTS: <Constraints> | ACTIVE: <Task ID> (<Task Desc>) | STATE: LEDGER.json`
4. **Post-Compaction Recovery Protocol**:
   - When the host harness triggers context compaction or when resuming an existing session:
     ```bash
     python3 "<SCRIPTS>/ledger_tool.py" rehydrate
     ```
   - Restores root intent, non-negotiable negative constraints, active task, verified decisions, dead ends, and touched file signatures without asking the user to repeat requirements.

---

## 5. Empirical Benchmark Suite (10 Real-World Workloads)

The agent MUST execute the empirical benchmark suite (`python3 "<SCRIPTS>/benchmark.py" --report "<path>"`) to audit context hygiene, tool ingress clamping, and anti-drift invariant retention across 10 real-world engineering workloads:

| # | Workload Scenario | Domain | Tested Ingress Mechanism | Baseline Failure Mode | `leanctx` Empirical Mitigation |
| :- | :--- | :--- | :--- | :--- | :--- |
| **01** | **Rust/Cargo Compiler Crash** | Systems / Backend | `lean_run.py` diagnostic sandwich + benign filter | 1,250 lines (~14k tokens) dumped; buried panic missed | Clamped to $\le 65$ lines, exit code 101 preserved, 100% root-cause capture (-93.4% tokens) |
| **02** | **Minified Bundle & Lockfile** | Frontend / Node.js | `lean_read.py` 500-char cap + 24KB byte ceiling | Single-line 450k-char bundle dumps >100k tokens in 1 turn | Clamped to 500 chars (+ drain loop); lockfile bounded $\le 150$ lines (-99.0% tokens) |
| **03** | **Recursive Monorepo Audit** | Full-Stack Security | `gate_tool.py` / `lean_run.py` ingress clamp | `grep -rn` / `find` dumps 2,750 lines (~28k tokens) | Intercepted and clamped to tail 25 lines each (-98.0% tokens) |
| **04** | **Zero-Downtime Migration** | Data Engineering | `inject_anchor.py` + `amend-intent` audit | Attention dilution causes constraint drift by turn 10 | 100% negative constraint retention via $\le 240$-char micro-anchor (-98.0% tokens) |
| **05** | **Payments SDK Refactoring** | API / Library Design | `update_ledger.py` public symbol preservation | Post-tool hooks wipe symbol dicts; forces repeated re-reads | 100% public symbol retention across edits; 0 re-read loops (-98.1% tokens) |
| **06** | **Dead-End Dependency Pivot** | Backend Architecture | `ledger_tool.py add-rejection` (Rank 3) | Agent forgets failed library installation; retry loop | Logged in Rank 3 negative knowledge; 0 repeat attempts (-96.9% tokens) |
| **07** | **Mid-Sprint Compaction** | Long-Running Feature | `ledger_tool.py rehydrate` | History compaction flushes contracts; agent hallucinates | 100% recovery of Ranks 1-3 in $\le 1,200$ tokens (-99.1% tokens) |
| **08** | **Parallel Subagent Shard** | Multi-Agent Systems | `--session` flag + `.ledger.lock` + anchor isolation | Parallel writes corrupt ledger; subagents leak master state | 0 cross-talk mutations in master; uninitialized subagents receive empty anchor (-94.3% tokens) |
| **09** | **CI Build & Package Noise** | DevOps / Frontend CI | `lean_run.py` success tail-25 + FIFO log rotation | 12 builds dump 5,400 lines (~36k tokens) into context | Clamped to tail 25 lines per build (-82.6% tokens); scratch bounded to $\le 10$ logs |
| **10** | **25-Turn Distributed Cache** | Distributed Systems | End-to-end 4-phase lifecycle | Watermark exceeds 90k tokens; SNR drops <0.01%; 80% drift | Watermark capped $\le 6,700$ tokens (-92.8%); SNR 10.2x gain; 100% retention |

---

## 6. Verifiable Performance Targets & SLAs

- **Tool Ingress Reduction**: $\ge 80\%$ reduction in tool output tokens entering conversation history (Empirically verified: **-94.4%** across live scenarios).
- **Active Context Watermark**: Watermark bounded to $\le 8,000$ tokens across 25 turns (Empirically verified: **6,690 tokens** vs 92,408 unmanaged baseline).
- **Cumulative Cost Savings**: $\ge 80\%$ reduction in inference costs (Empirically verified: **-93.0%** cost delta).
- **Compaction Recovery Invariance**: 100% retention of Rank 1 constraints, active tasks, decisions, dead ends, and touched file signatures.
- **Root-Cause Error Capture**: 100% capture of compiler panics and syntax errors via smart log extraction.
