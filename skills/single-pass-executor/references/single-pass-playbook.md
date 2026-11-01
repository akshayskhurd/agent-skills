# Single-Pass Execution Playbook

## 1. Upfront Invariant Formulation

Before writing target code, the agent MUST explicitly define:
- **Input Contracts**: Types, ranges, nullability, empty states.
- **Output Contracts**: Strict JSON schema, function return signature, exception types.
- **State Invariants**: Pre-conditions that MUST hold true before execution; post-conditions that MUST hold true after.

## 2. Boundary Condition Scrutiny Matrix

Every algorithm or function MUST pass verification against this matrix:

| Condition | Verification Requirement |
| :--- | :--- |
| **$N = 0$ / Empty** | MUST handle empty arrays, empty strings, and empty dicts without index exceptions. |
| **$N = 1$ / Singleton** | MUST handle single-element inputs without off-by-one errors. |
| **`None` / Null** | MUST perform explicit null-checking before property access. |
| **Concurrency / Re-entrancy** | MUST isolate mutating state to prevent race conditions. |
| **Error Propagation** | MUST raise explicit domain exceptions instead of returning generic nulls. |

## 3. Structured Scratchpad Protocol

The in-context scratchpad MUST follow this strict sequence:
1. **Contract Extraction**: Enumerate parameter types and schema definitions.
2. **Failure Analysis**: Enumerate 3 most likely failure scenarios for this specific task.
3. **Execution Plan**: Numbered sequence of deterministic actions.
4. **Synthesis**: Final production code or artifact.
