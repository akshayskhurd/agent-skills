# The Convergence Protocol: Review-and-Fix Loop

The Grill skill enforces an autonomous, iterative convergence loop. Remediation does not end when fixes are drafted; it ends only when an exhaustive re-audit detects **zero defects, zero security gaps, and zero ambiguities**, while verifying **100% semantic invariance**.

---

## 1. Loop Lifecycle & State Machine

```
              ┌───────────────────────────┐
              │   Pass 0: Ingestion &     │
              │   Baseline Line Counting  │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │ Pass N: 9-Persona Grilling│◄──────────────┐
              └─────────────┬─────────────┘               │
                            │                             │
              ┌─────────────▼─────────────┐               │
              │  Issue Detection Matrix   │               │
              └─────────────┬─────────────┘               │
                            │                             │
                     Issues Found?                        │
                     /          \                         │
               [YES]              [NO]                    │
                 │                  │                     │
      ┌──────────▼──────────┐       │                     │
      │ Surgical Remediation│       │                     │
      └──────────┬──────────┘       │                     │
                 │                  │                     │
      ┌──────────▼──────────┐       │                     │
      │ Semantic Invariance │       │                     │
      │   & Regression Check│       │                     │
      └──────────┬──────────┘       │                     │
                 │                  │                     │
                 └──────────────────┘                     │
                                                          │
                                            ┌─────────────▼─────────────┐
                                            │ Final Zero-Defect Verdict │
                                            └───────────────────────────┘
```

---

## 2. Step-by-Step Loop Execution

### Step 1: Ingestion & Baseline Capture
- Read the entire file or artifact without skipping any lines.
- Record the exact line count, exported symbols, public APIs, and documented goals.
- Establish the baseline behavioral invariant: *"What must this component do?"*

### Step 2: Line-by-Line Persona Audit (Pass N)
- Walk sequentially through every line $1 \dots L$.
- Apply all 9 personas and 5W1H counter-questions.
- Populate the **Issue Detection Matrix**:
  ```text
  [PASS N - ISSUE #1]
  Line: 48
  Persona: Security Researcher
  Finding: Unsanitized user parameter passed directly to subprocess.run(shell=True)
  5W1H Counter-Question: What if user_input contains "; rm -rf /" or shell operators?
  Imperative Directive: MUST set shell=False and pass arguments as a validated list.
  ```

### Step 3: Surgical Remediation
- Apply fixes directly to the source file or document using `edit_file` or `write_file`.
- Every fix **MUST** be minimal, defensive, and targeted.
- Do not introduce cosmetic style changes or personal aesthetic preferences unrelated to defects or maintainability.

### Step 4: Semantic Invariance & Regression Check
Before proceeding to the next pass, the agent **MUST** verify the 3 Semantic Invariant Rules:
1. **Signature Invariant**: Did any public function, method, or class signature break?
   - If yes: Revert and adapt fix to preserve external compatibility.
2. **Contract Invariant**: Does the code still satisfy all original business requirements?
   - If yes: Proceed.
   - If no: Fix violates semantic preservation; rewrite fix.
3. **Purity Invariant**: Did the fix introduce new unhandled exceptions or hidden side effects?
   - If yes: Flag as a new defect for the next pass.

### Step 5: Termination, Circuit Breaking, or Recurse
- If issues were found and fixed in Pass $N$, the agent **MUST** execute Pass $N+1$.
- Pass $N+1$ scrutinizes the updated code from line 1 to the end.
- If Pass $N+1$ uncovers secondary defects (e.g., a newly added parameter is unvalidated), fix and repeat.
- **Circuit Breaker Constraint**: The loop **MUST NEVER** exceed 5 passes ($N \le 5$). If pass 5 completes with remaining defects, the agent **MUST** abort further autonomous modifications and output an Escalation Matrix detailing the oscillating or conflicting requirements.
- **Termination Condition**: When Pass $K$ ($K \le 5$) completes with **0 issues across all 9 personas**, the loop terminates with Zero-Defect Certification.

---

## 3. Large-Artifact & Multi-File Windowing Protocol

When grilling targets exceeding single-context limits:
1. **Module Decomposition**: Decompose the repository or file into functional sub-modules based on the dependency graph (DAG).
2. **Bottom-Up Interrogation**: Grill leaf modules first. Ensure lower-level contracts are airtight before grilling parent orchestration modules.
3. **Subagent Delegation**: For repositories with $>1,000$ lines, launch a dedicated subagent (`invoke_subagent` with `role: "Codebase Researcher"`) to extract exact call graphs and line numbers before beginning Phase 2.

---

## 4. Handling User Architectural Clarifications

If a defect stems from an irreconcilable ambiguity in requirements (e.g., two mutually exclusive business specifications), the agent **MUST**:
1. Present the conflict clearly to the user.
2. State the exact trade-offs (e.g., Option A vs Option B).
3. Recommend the optimal path prefixed with `(Recommended)`.
4. Await user confirmation before altering structural business assumptions.
