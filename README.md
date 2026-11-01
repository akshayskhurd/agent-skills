# Agent Skills Toolkit

Production-grade, token-optimized skills designed for autonomous AI coding assistants (Google Antigravity, Claude Code, Codex, and Agentic frameworks).

Every skill in this repository is built on **two-tier progressive disclosure**, enforces **strictly imperative directives** (`MUST`, `NEVER`, `ALWAYS`), and has been verified with the **Grill Protocol** for zero-defect reliability.

---

## 📦 Included Skills

| Skill | Category | Description | Primary CLI / Script |
| :--- | :--- | :--- | :--- |
| **[`deep-tester`](./skills/deep-tester)** | Quality Engineering | Universal multi-vector test engineer for functional, security, resource, asymptotic, and matrix testing in any language. | `python3 scripts/matrix_generator.py` |
| **[`telescope`](./skills/telescope)** | Orchestration | Dual-lens orchestrator bridging macro architecture docs with micro single-pass tasks and dual-layer grill audits. | `python3 scripts/orchestrate_dag.py` |
| **[`skill-creator`](./skills/skill-creator)** | Meta-Tooling | Scaffold, author, and validate new agent skills with strict frontmatter and token constraints. | `python3 scripts/scaffold_skill.py` |
| **[`single-pass-executor`](./skills/single-pass-executor)** | Execution | Enforce first-pass accuracy and eliminate trial-and-error debugging via upfront contracts and static gates. | `python3 scripts/verify_contracts.py` |
| **[`grill`](./skills/grill)** | Review & Audit | Exhaustive 9-persona 5W1H adversarial review and surgical remediation loop for code, PRs, and plans. | `python3 scripts/grill_checker.py` |
| **[`learn`](./skills/learn)** | Memory & Rules | Autonomously extract, distill, and persist user corrections and operational breakthroughs into persistent rules. | `python3 scripts/instruction_updater.py` |

---

## 🚀 Multi-Harness Automated Installation

Zero manual copying. Install, symlink, audit, and provision skills across **Claude Code**, **OpenCode**, **Codex / OpenAI**, **Pi Agent**, **Google Antigravity / Gemini CLI**, and **Universal Agents**.

### 1. One-Liner Zero-Dependency Installer (Auto-Detects All Harnesses)
Requires NO Python or package managers. Runs pure POSIX shell (`mkdir`, `cp`, `ln`):

```bash
# Auto-detects installed harnesses on your machine and deploys all skills
curl -fsSL https://raw.githubusercontent.com/akshayskhurd/agent-skills/main/install.sh | bash
```

### 2. Claude Code Plugin Marketplace
Install directly via Claude Code's native plugin manager:

```bash
claude plugin marketplace add akshayskhurd/agent-skills
claude plugin install agent-skills
```

### 3. Local Clone or Specific Harness Provisioning
Target specific agent platforms or use live development symlinks:

```bash
# Clone the repository
git clone https://github.com/akshayskhurd/agent-skills.git
cd agent-skills

# Target specific harnesses (claude, opencode, codex, pi, gemini, agents)
./install.sh --target claude,opencode,codex,pi

# Live sync mode (symlinks back to repo so git pulls update skills automatically)
./install.sh --symlink

# Project-local installation (into .agents/skills or .claude/skills in current directory)
./install.sh --local --target agents

# Audit installed skills across all harnesses on this machine
./install.sh --status
```

### 4. Git Submodule (Universal Agent RFC Standard)
Mount skills natively in any repository without running scripts:

```bash
git submodule add https://github.com/akshayskhurd/agent-skills.git .agents/skills/agent-skills
```

### 5. Python Installer CLI (Alternative)
For Windows or systems with Python 3:

```bash
python3 install.py --target auto
python3 install.py --status
```

---

## 🛠️ CLI Utilities & Workflows

### 1. Initialize Dual-Lens Telescope Perspective & DAG
```bash
# Initialize living perspective tracking
python3 skills/telescope/scripts/orchestrate_dag.py init \
  --project "Webhook System" \
  --objective "Build resilient rate-limited webhook dispatcher"

# Add low-level tasks to the execution DAG
python3 skills/telescope/scripts/orchestrate_dag.py add-task \
  --id "task-1" --title "Payload Signer" --spec "HMAC SHA-256 serializer"

# Render living macro perspective document
python3 skills/telescope/scripts/orchestrate_dag.py render
```

### 2. Scaffold a New Agent Skill
```bash
python3 skills/skill-creator/scripts/scaffold_skill.py scaffold \
  --name "docker-deploy" \
  --description "Use this skill when building and deploying Docker services to staging." \
  --scope workspace
```

### 2. Generate Permutative & Pairwise Test Matrices
```bash
# Generate Python pytest parameterized matrix
python3 skills/deep-tester/scripts/matrix_generator.py \
  '{"role": ["admin", "guest"], "status": ["active", "suspended"]}' \
  --format pytest

# Generate Go table-driven test matrix
python3 skills/deep-tester/scripts/matrix_generator.py \
  '{"role": ["admin", "guest"], "count": [1, 5]}' \
  --format go

# Generate Jest / Vitest test matrix
python3 skills/deep-tester/scripts/matrix_generator.py \
  '{"role": ["admin", "guest"], "active": [true, false]}' \
  --format jest
```

### 3. Validate Existing Skills for Directive & Schema Compliance
```bash
python3 skills/skill-creator/scripts/scaffold_skill.py validate skills/single-pass-executor
```

### 3. List All Discovered Skills
```bash
python3 skills/skill-creator/scripts/scaffold_skill.py list --scope all
```

### 4. Run Single-Pass Static Contract Verifier
```bash
python3 skills/single-pass-executor/scripts/verify_contracts.py path/to/source_or_directory
```

### 5. Run Grill Adversarial Code & Directive Checker
```bash
python3 skills/grill/scripts/grill_checker.py --file path/to/file.py
```

---

## 🧪 Testing & Verification

Run the automated test suites covering edge cases, DAG states, block scalar parsing, collision handling, and AST verification:

```bash
# Test skill scaffolding and directive verification
python3 skills/skill-creator/tests/test_skills.py

# Test telescope DAG orchestration and perspective rendering
python3 skills/telescope/tests/test_telescope.py

# Test deep-tester combinatorial matrix generator and formatters
python3 skills/deep-tester/tests/test_deep_tester.py
```

---

## 🛡️ Privacy & Security Compliance

- **Zero PII**: No hardcoded personal emails, usernames, machine hostnames, or absolute local user paths.
- **Portable**: Works across macOS, Linux, and Windows environments using relative and home-relative paths.
- **Zero External Dependencies**: All CLI utilities run on standard Python 3.8+ libraries without requiring external packages.

---

## 📄 License

MIT License. See [LICENSE](./LICENSE) for details.
