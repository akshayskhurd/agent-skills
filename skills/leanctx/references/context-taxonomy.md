# The 6-Tier Context Retention Taxonomy

To eliminate context bloat and prevent model drift across long-running sessions, all information entering or existing within the agent's context window MUST be categorized and governed by the following deterministic 6-tier retention hierarchy.

---

## 1. Context Priority Tiers

| Rank | Priority Level | Context Category | Typical Payload | Retention & Eviction Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Rank 1** | **CRITICAL (100%)** | **Root Intent & Invariant Rules** | User acceptance criteria, system rules (`GEMINI.md`, `CLAUDE.md`), immutable architectural constraints. | **ALWAYS KEEP**. MUST NEVER be evicted, compacted, or mutated. Serves as the primary anti-drift anchor. |
| **Rank 2** | **OPERATIONAL (90%)** | **Active Task & Blocker State** | Current DAG milestone, active sub-task objective, unresolved compiler error currently under fix. | **ALWAYS KEEP UNTIL RESOLVED**. Dynamically updated when task transitions to `DONE`. |
| **Rank 3** | **SEMANTIC (75%)** | **Living Ledger & Interface Contracts** | Touched file paths, modified API signatures, verified technical facts, architectural decisions. | **CONDENSE & KEEP**. Persisted atomically in `.agents/memory/LEDGER.json`. Historical syntax stripped. |
| **Rank 4** | **TRANSIENT (50%)** | **Immediate Operational Buffer** | Turn $N-1$ and Turn $N$ user inputs, immediate prior tool invocation arguments and direct output. | **ROLLING BUFFER**. Kept strictly for conversational flow. Evicted once execution advances past $N-2$. |
| **Rank 5** | **EPHEMERAL (20%)** | **Exploratory & Static File Reads** | Raw `read_file` line dumps, AST dumps, file search results (`grep`, `find`), directory listings. | **EVICT UPON CONSUMPTION**. Target lines extracted to Rank 3; raw line dumps discarded immediately. |
| **Rank 6** | **NOISE (0%)** | **Disposable Execution Noise** | Verbose stdout/stderr of passing builds, linter runs, package installations (`npm`, `pip`), resolved syntax errors. | **IMMEDIATE DISCARD**. 0% long-term persistence. Redirected to `/tmp/leanctx/`; only binary status or diagnostic sandwich kept. |

---

## 2. Ingress & Eviction Mechanics

### Ingress Prevention (Ranks 5 & 6)
- **Pre-execution Clamping**: Command outputs exceeding 30 lines MUST NOT enter history in full. Commands are wrapped to write raw streams to disk, emitting only summary or Head/Tail diagnostic sandwiches.
- **Line Budget Bounds**: Large files MUST NOT be ingested wholesale. File reads without explicit ranges MUST be clamped to a maximum budget ($\le 150$ lines).

### State Distillation (Ranks 2 & 3)
- When a task or milestone completes, the agent MUST write state updates to `.agents/memory/LEDGER.json` and prune ephemeral trial-and-error chatter.
- Historical file diffs and tool logs are consolidated into semantic summaries (e.g. `"Updated auth token validation in auth.py"`).

### Micro-Anchor Injection (Rank 1 & 2)
- To prevent attention drift without inflating context, the agent MUST inject or maintain a bounded 1-line anchor:
  ```text
  [leanctx-anchor] GOAL: <Root Goal> | ACTIVE: <Task ID> | STATE: .agents/memory/LEDGER.json
  ```
- Detailed facts MUST remain on disk and be read on demand.
