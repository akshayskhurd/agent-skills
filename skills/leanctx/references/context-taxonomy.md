# The 6-Tier Context Retention Taxonomy

To eliminate context bloat and prevent model drift across long-running sessions, all information entering or existing within the agent's context window MUST be categorized and governed by the following deterministic 6-tier retention hierarchy.

---

## 1. Ground Truth: Ingress Suppression vs. Compaction Re-Hydration

An LLM cannot delete messages from its own conversational history once ingested. Context hygiene in `leanctx` is achieved through two mechanical gates:
1. **Ingress Suppression (Ranks 5 & 6)**: Noisy outputs are intercepted *before* they enter history. Raw tool streams are written to disk, emitting only concise summaries or targeted error context into the prompt.
2. **Compaction Re-Hydration (Ranks 1–3)**: When the host harness compacts the session (e.g. `/compact` or auto-compaction), the agent re-hydrates verified goals, decisions, and file states directly from `.agents/memory/LEDGER.json`, preventing loss of context or drift.

---

## 2. Context Priority Tiers

| Rank | Priority Level | Context Category | Typical Payload | Ingress & Retention Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Rank 1** | **CRITICAL (100%)** | **Root Intent & Invariant Rules** | User acceptance criteria, system rules (`GEMINI.md`, `CLAUDE.md`), immutable architectural constraints. | **ALWAYS PRESERVED ON DISK & ANCHOR**. Maintained in `LEDGER.json`. Re-injected via micro-anchor on every turn. |
| **Rank 2** | **OPERATIONAL (90%)** | **Active Task & Blocker State** | Current DAG milestone, active sub-task objective, unresolved compiler error currently under fix. | **PRESERVED UNTIL RESOLVED**. Updated in `LEDGER.json` as tasks complete. |
| **Rank 3** | **SEMANTIC (75%)** | **Living Ledger & Interface Contracts** | Touched file paths, modified API signatures, verified technical facts, architectural decisions. | **CONDENSED ON DISK**. Persisted atomically in `LEDGER.json`. Restored via `ledger_tool.py rehydrate` post-compaction. |
| **Rank 4** | **TRANSIENT (50%)** | **Immediate Operational Buffer** | Conversational back-and-forth, immediate prior user inputs, and immediate tool results. | **WORKING BUFFER**. Naturally compacts when host harness summarizes or rolls context window. |
| **Rank 5** | **EPHEMERAL (20%)** | **Exploratory & Static File Reads** | Code extracts, AST outlines, search results (`grep`, `find`), directory listings. | **INGRESS CLAMPED**. Large files are clamped ($\le 150$ lines). Relevant lines distilled to Rank 3; raw dumps never enter context. |
| **Rank 6** | **NOISE (0%)** | **Disposable Execution Noise** | Verbose stdout/stderr of passing builds, linter runs, package installations (`npm`, `pip`), compiler warnings. | **INGRESS SUPPRESSED**. Redirected to `/tmp/leanctx/<id>/last_exec.log`. Emits only binary status or root-cause error context. |

---

## 3. Ingress & Re-Hydration Protocol

### Ingress Noise Suppression (Ranks 5 & 6)
- **Pre-execution Sandboxing**: High-volume commands MUST NOT dump raw output into the context window. Commands are wrapped to write to disk, emitting only summary headers or root-cause error lines.
- **Line Budget Bounds**: Large files MUST NOT be ingested wholesale. File reads without explicit bounds MUST be clamped to a maximum budget ($\le 150$ lines).

### Post-Compaction Re-Hydration Protocol (Ranks 1–3)
- When starting a resumed session or following context compaction:
  1. The agent MUST NOT ask the user to restate requirements or re-explore code.
  2. The agent MUST execute `ledger_tool.py rehydrate` or read `.agents/memory/LEDGER.json`.
  3. The agent restores active milestone state and continues execution immediately.
