# The 6-Tier Context Retention Taxonomy

To eliminate context bloat and prevent model drift across long-running sessions, all information entering or existing within the agent session MUST be categorized and governed by the following deterministic 6-tier retention hierarchy.

---

## 1. Ground Truth: Agent-Enforced Ingress vs. Harness-Enforced Compaction

An LLM cannot evict or delete messages from its own conversational context once ingested. Context optimization in `leanctx` is strictly divided into two operational domains:

1. **Agent-Enforced Responsibilities (Ingress Prevention & State Offload)**:
   - **Ingress Clamping (Ranks 5 & 6)**: The agent intercepts verbose file reads and command outputs *before* they enter history. Raw tool outputs write to disk; only concise summaries or targeted diagnostic sandwiches enter conversation history.
   - **State Offload (Ranks 1–3)**: The agent writes invariant intents, active milestone state, verified public symbols, and negative knowledge (dead ends) directly to `.agents/memory/LEDGER.json`.
   - **Context Anchoring**: The agent emits a single-line micro-anchor containing root goal, non-negotiable negative constraints, and active DAG task on every turn.

2. **Harness-Enforced Responsibilities (Buffer Truncation & Compaction)**:
   - **Buffer Windowing (Rank 4)**: The client harness (Claude Code, Antigravity, OpenCode, Pi, Codex) manages active conversation window bounds and rolling turn summaries.
   - **Compaction Rehydration**: When the host harness triggers session compaction (or upon session resumption), the agent MUST run `ledger_tool.py rehydrate` to rebuild Ranks 1–3 into prompt memory without user re-prompting.

---

## 2. Context Priority Tiers & Concrete Budgets

| Rank | Retention Tier | Context Category | Typical Payload | Concrete Budget & Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Rank 1** | **IMMUTABLE INTENT** | **Root Intent & Invariant Rules** | User acceptance criteria, system rules (`GEMINI.md`), non-negotiable negative constraints. | **$\le 500$ tokens on disk**. Immutable to autonomous agent drift. Mutated ONLY via explicit user authorization logged in `ledger_tool.py amend-intent`. Emitted in every micro-anchor. |
| **Rank 2** | **ACTIVE OPERATIONAL** | **Active Task & Blocker State** | Current DAG milestone, active sub-task objective, unresolved compiler error currently under fix. | **$\le 500$ tokens on disk**. Preserved until resolved. Demoted to Rank 3 upon task completion. |
| **Rank 3** | **SEMANTIC LEDGER** | **Contracts, Signatures & Dead Ends** | Modified file paths with public exported signatures, verified technical decisions, and rejected dead-end paths. | **$\le 1,500$ tokens on disk**. Persisted atomically in `LEDGER.json`. Must preserve exact public signatures (stripping implementation bodies) and dead ends to eliminate re-read and retry loops. |
| **Rank 4** | **TRANSIENT BUFFER** | **Conversational Working Memory** | Conversational back-and-forth, immediate prior user inputs, and immediate tool results. | **$\le 4,000$ tokens in context**. Harness-managed rolling turns. Naturally compacted when host harness triggers context compaction. |
| **Rank 5** | **EPHEMERAL READS** | **Exploratory & Static File Reads** | Code extracts, AST outlines, search results (`grep`, `find`), directory listings. | **Clamped $\le 150$ lines/read**. Unbounded file reads are strictly prohibited. Relevant public signatures are distilled to Rank 3; raw lines never re-enter context. |
| **Rank 6** | **DISPOSABLE NOISE** | **Execution & Build Noise** | Verbose stdout/stderr of builds, test suites, linter runs, package installations (`npm`, `cargo`, `pip`). | **Clamped $\le 50$ lines in context**. Raw stream redirected to `<SCRATCH>/last_exec.log`. Success emits tail 25 lines. Failure emits diagnostic sandwich (Head 15 + Root-cause error lines + Tail 15 $\le 65$ lines). |

---

## 3. Promotion & Demotion Lifecycle Rules

```
[Tool Execution] 
      │
      ├── File Read / Grep (Rank 5) ───[Uncovers Signature]────► Rank 3 (File & Public Symbol)
      │
      ├── Command Failure (Rank 6) ────[Identifies Blocker]────► Rank 2 (Active Blocker Task)
      │                                └──[Failed Approach]────► Rank 3 (Rejected Dead End)
      │
      └── Task Completion (Rank 2) ───[Demote Milestone]──────► Rank 3 (Verified Decision + Contract)
```

1. **Discovery &rarr; Rank 2 / Rank 3 Promotion**:
   - When a Rank 5 file read or search reveals an active blocker, the agent MUST immediately promote the finding to Rank 2 via `ledger_tool.py set-task`.
   - When a Rank 5 file read introduces or updates a public interface, the agent MUST immediately record the signature in Rank 3 via `ledger_tool.py add-file --file <path> --symbols "<signature>"`.
2. **Failure &rarr; Rank 3 Dead End Promotion**:
   - When an attempted implementation fails or a dependency proves incompatible, the agent MUST NOT discard the lesson. The agent MUST record the failure in Rank 3 via `ledger_tool.py add-rejection --approach "<attempted approach>" --reason "<failure reason>"` to prevent re-attempting dead ends.
3. **Milestone Completion & Demotion**:
   - When a Rank 2 active task completes, the agent MUST record verified decisions and touched file signatures into Rank 3, then update Rank 2 to the subsequent DAG milestone.
4. **Disposal**:
   - Raw Rank 5 and Rank 6 disk logs in `<SCRATCH>/` expire automatically via FIFO rotation (maximum 10 files) and MUST NEVER be promoted to persistent memory.

---

## 4. Ingress Clamping Specifications

### Command Output Clamping (Rank 6)
- Passing commands ($\text{exit code} = 0$):
  - Outputs $\le 30$ lines: Emitted in full.
  - Outputs $> 30$ lines: Clamped to tail 25 lines.
- Failing commands ($\text{exit code} \ne 0$):
  - Outputs $\le 50$ lines: Emitted in full.
  - Outputs $> 50$ lines: Clamped to Head 15 lines + Root-cause error context (up to 35 lines) + Tail 15 lines. Total output MUST NOT exceed 65 lines.
  - Full output MUST ALWAYS be redirected to `<SCRATCH>/last_exec.log`.

### File Reading Clamping (Rank 5)
- All file reads MUST be bounded to $\le 150$ lines.
- Unbounded reads of files exceeding 150 lines MUST be clamped to the initial 150 lines.

### Micro-Anchor Format (Anti-Drift Invariant)
Every turn MUST include the active micro-anchor containing root intent, constraints, and active task:
```
[leanctx-anchor] GOAL: <Goal> | CONSTRAINTS: <Constraint 1>; <Constraint 2> | ACTIVE: <Task ID> (<Task Desc>) | STATE: LEDGER.json
```
