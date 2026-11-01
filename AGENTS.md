# Agent Skills Toolkit — Antigravity Workspace Directives

## 1. Project Overview & Architecture
This repository provides production-grade, token-optimized agent skills designed for autonomous AI coding agents (Google Antigravity, Claude Code, OpenCode, Codex, and Pi).

Every skill is built on two-tier progressive disclosure, strictly imperative directives (`MUST`, `NEVER`, `ALWAYS`), and verified via the Grill Protocol.

---

## 2. Mandatory Authoring Directives
- **Zero-Hedge Directives**: ALL skills, instructions, scripts, and documentation MUST use strictly imperative verbs (`MUST`, `NEVER`, `ALWAYS`). NEVER use hedge words (`might`, `probably`, `consider`, `maybe`).
- **High Token Density**: NEVER write wasteful ASCII art, redundant greetings, or repetitive boilerplate. Ensure maximum information density.
- **Strict AST Sandboxing**: NEVER execute unvalidated dynamic evaluation (`eval()`, `exec()`, `shell=True`). All runtime expression filters MUST traverse safe AST nodes (`ast.Constant`, `ast.Name`, `ast.Compare`, `ast.BoolOp`, `ast.UnaryOp`, `ast.List`, `ast.Tuple`).
- **Zero Secret / PII Leaks**: NEVER commit personal email addresses or hostnames. All commits MUST use `akshayskhurd <34104737+akshayskhurd@users.noreply.github.com>`.

---

## 3. Included Skills & Primary Entry Points
1. **`deep-tester`**: Multi-vector test engineer (`skills/deep-tester/scripts/matrix_generator.py`).
2. **`telescope`**: Dual-lens macro-DAG orchestrator (`skills/telescope/scripts/orchestrate_dag.py`).
3. **`skill-creator`**: Meta-skill scaffolder and auditor (`skills/skill-creator/scripts/scaffold_skill.py`).
4. **`single-pass-executor`**: Zero-defect contract executor (`skills/single-pass-executor/scripts/verify_contracts.py`).
5. **`grill`**: Exhaustive 9-persona 5W1H adversarial review gate (`skills/grill/scripts/grill_checker.py`).
6. **`learn`**: Memory and rule distillation engine (`skills/learn/scripts/instruction_updater.py`).

---

## 4. Verification & Quality Gates
Before any pull request or commit, the agent MUST run:
```bash
# Run entire test suite
python3 -m unittest discover -s tests -v
python3 skills/skill-creator/tests/test_skills.py
python3 skills/telescope/tests/test_telescope.py
python3 skills/telescope/tests/verify_scenarios.py
python3 skills/deep-tester/tests/test_deep_tester.py

# Run Grill audit on modified files
python3 skills/grill/scripts/grill_checker.py --file <file>
```
