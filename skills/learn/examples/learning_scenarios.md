# Learning & Distillation Scenarios

Walkthroughs of how raw conversation turns are distilled into persistent instructions.

---

## Scenario 1: User Correction on Tooling

**User Statement**:
> *"Never run npm install directly in this repo, we strictly use `pnpm install --frozen-lockfile` to prevent lockfile desync."*

**Analysis**:
- Scope: Workspace (`<workspace>/GEMINI.md`)
- Category: `Tooling, Build & Package Management`
- Directive: `ALWAYS use 'pnpm install --frozen-lockfile' instead of npm or yarn.`
- Rationale: `Prevents package lockfile drift and guarantees reproducible dependencies.`

**Execution**:
```bash
python3 ~/.gemini/config/skills/learn/scripts/instruction_updater.py \
  --file ./GEMINI.md \
  --category "Tooling, Build & Package Management" \
  --rule "ALWAYS use 'pnpm install --frozen-lockfile'; NEVER invoke npm or yarn directly." \
  --rationale "Prevents package lockfile drift and guarantees reproducible dependency resolution."
```

---

## Scenario 2: Debugging Quirk Resolution

**Context**:
After 3 attempts debugging an esoteric SQLite lock error during tests, the agent discovers:
> *"SQLite in WAL mode on NFS mounts fails with disk I/O error unless `busy_timeout` is set to 5000ms."*

**Analysis**:
- Scope: Workspace (`<workspace>/GEMINI.md`)
- Category: `Testing & Quality Verification`
- Directive: `ALWAYS configure SQLite connections with 'busy_timeout=5000' during test suites.`
- Rationale: `Avoids spurious disk I/O lock errors caused by NFS filesystem latency.`

---

## Scenario 3: Global Coding Preference

**User Statement**:
> *"In all my Python code, I hate nested conditionals. Always use guard clauses and return early."*

**Analysis**:
- Scope: Global (`~/.gemini/GEMINI.md`)
- Category: `Coding Standards & Idioms`
- Directive: `ALWAYS use guard clauses and early returns; keep nesting levels <= 2.`
- Rationale: `Reduces cognitive complexity and enforces clean control flow.`
