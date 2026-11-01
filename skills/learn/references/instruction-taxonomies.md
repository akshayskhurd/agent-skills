# Instruction Taxonomies & Distillation Rubric

Persistent instructions alter all future agent behaviors. Follow this rubric to decide what to learn, where to store it, and how to format it.

---

## 1. Storage Scope Decision Tree

```
                                Learning Signal Detected
                                           │
                  ┌────────────────────────┴────────────────────────┐
                  ▼                                                 ▼
        Is it specific to one                           Is it universal across all
        repository or codebase?                         projects on this machine?
                  │                                                 │
                  ▼                                                 ▼
       [WORKSPACE SCOPE]                                     [GLOBAL SCOPE]
       File: <workspace>/GEMINI.md                           File: ~/.gemini/GEMINI.md
       (or .agents/rules/*.md)                               
                  │
                  ▼
   Does it describe a complex
   multi-step runbook (>5 steps)?
                  │
        [YES] ───┴───► [SKILL SCOPE]
                       File: skills/<name>/SKILL.md
```

---

## 2. Signal vs. Noise Filter

| Signal (PERSIST THIS) | Noise (DO NOT PERSIST) |
|---|---|
| User correction: *"Don't use yarn here, we always use pnpm."* | One-off bug: *"Fix line 42 typo."* |
| Discovered quirk: *"In this repo, tests must run with `--runInBand`."* | Transient data: *"My test API key is xyz."* |
| Architectural invariant: *"All DB queries must go through QueryBuilder."* | Temporary task: *"Draft an email to Bob."* |
| Personal preference: *"Prefer concise functional TypeScript with fp-ts."* | Conversational banter: *"Thanks, that looks great."* |

---

## 3. Standard Rule Formatting

Rules **MUST** follow the canonical high-density format:

```markdown
## <Category Name>

- **<IMPERATIVE DIRECTIVE>**
  *Rationale*: <One concise sentence explaining why this rule exists.>
```

### Approved Categories
1. `Coding Standards & Idioms`
2. `Testing & Quality Verification`
3. `Architecture & Contract Invariants`
4. `Tooling, Build & Package Management`
5. `Security & Secrets Handling`
6. `User Preferences & Workflow Habits`
