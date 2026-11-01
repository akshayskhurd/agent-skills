#!/usr/bin/env python3
"""
Scaffolding and validation CLI for Antigravity skills.
Enforces imperative directives, valid YAML frontmatter, and standard layout.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

BANNED_HEDGE_PATTERNS = [
    re.compile(r"\bshould\b", re.IGNORECASE),
    re.compile(r"\bmight\b", re.IGNORECASE),
    re.compile(r"\bcould\b", re.IGNORECASE),
    re.compile(r"\btry to\b", re.IGNORECASE),
    re.compile(r"\bplease\b", re.IGNORECASE),
    re.compile(r"\bmaybe\b", re.IGNORECASE),
    re.compile(r"\bperhaps\b", re.IGNORECASE),
    re.compile(r"\bprobably\b", re.IGNORECASE),
    re.compile(r"\bpotentially\b", re.IGNORECASE),
    re.compile(r"\bcould consider\b", re.IGNORECASE),
]

TEMPLATE_SKILL_MD = """---
name: {name}
description: >-
  {description}
---

# {title}

{overview}

## 1. Trigger Conditions

The agent MUST activate this skill when:
1. The user requests "{name}" tasks or related workflows.
2. Conditions matching the skill description occur.

## 2. Procedural Workflow

### Phase 1: Pre-Flight Verification
- ALWAYS verify environment prerequisites before execution:
  ```bash
  # Check required tools
  ```

### Phase 2: Core Execution
- Step 1: Execute primary operations deterministically.
- Step 2: Offload bulky manuals to `[references/](./references/)`.

### Phase 3: Post-Execution Verification
- MUST validate the outcome against expected assertions.
- NEVER mark a task complete without deterministic verification.
"""


def find_workspace_root(start_dir: Optional[Path] = None) -> Path:
    """Traverse up to find repository root containing .git or .agents."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / ".git").exists() or (parent / ".agents").exists():
            return parent
    return curr


def parse_frontmatter(content: str) -> Tuple[Optional[str], Optional[dict]]:
    """Parse YAML frontmatter without external pyyaml dependency."""
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not fm_match:
        return None, None

    fm_raw = fm_match.group(1)
    fm_data = {}

    # Extract name
    name_match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", fm_raw, re.MULTILINE)
    if name_match:
        fm_data["name"] = name_match.group(1).strip()

    # Extract description (handles single-line and multiline block scalars: >-, >, |)
    desc_match = re.search(
        r"^description:\s*(?:>-|>|\|)?\s*\n?((?:^[ \t]+[^\n]+\r?\n?)+)",
        fm_raw,
        re.MULTILINE,
    )
    if desc_match:
        lines = [line.strip() for line in desc_match.group(1).splitlines() if line.strip()]
        fm_data["description"] = " ".join(lines)
    else:
        single_desc = re.search(r"^description:\s*([^\n]+)$", fm_raw, re.MULTILINE)
        if single_desc:
            clean_desc = single_desc.group(1).strip().strip("'\"")
            if clean_desc and clean_desc not in (">-", ">", "|"):
                fm_data["description"] = clean_desc

    return fm_raw, fm_data


def scaffold_skill(name: str, description: str, target_dir: Path, overwrite: bool = False) -> Path:
    skill_dir = target_dir / name
    if skill_dir.is_file():
        print(f"Error: Target path '{skill_dir}' is an existing file, not a directory.", file=sys.stderr)
        sys.exit(1)

    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not overwrite:
        print(f"Error: {skill_file} already exists. Pass --overwrite to replace.", file=sys.stderr)
        sys.exit(1)

    scripts_dir = skill_dir / "scripts"
    refs_dir = skill_dir / "references"
    examples_dir = skill_dir / "examples"

    for d in (skill_dir, scripts_dir, refs_dir, examples_dir):
        d.mkdir(parents=True, exist_ok=True)

    title = " ".join(word.capitalize() for word in name.replace("-", " ").split())
    content = TEMPLATE_SKILL_MD.format(
        name=name,
        description=description.strip(),
        title=title,
        overview=f"Operational procedure and deterministic runbook for {title}.",
    )

    try:
        skill_file.write_text(content, encoding="utf-8")
    except OSError as err:
        print(f"Error: Failed to write {skill_file}: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully scaffolded skill '{name}' at: {skill_dir}")
    return skill_dir


def validate_skill(skill_path: Path) -> bool:
    if skill_path.is_dir():
        skill_file = skill_path / "SKILL.md"
        skill_dir = skill_path
    else:
        skill_file = skill_path
        skill_dir = skill_path.parent

    if not skill_file.exists():
        print(f"Error: SKILL.md not found at {skill_file}", file=sys.stderr)
        return False

    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"Error: Failed to read {skill_file}: {err}", file=sys.stderr)
        return False

    errors: List[str] = []
    warnings: List[str] = []

    # Frontmatter validation
    fm_raw, fm_data = parse_frontmatter(content)
    if fm_raw is None or fm_data is None:
        errors.append("Missing or malformed YAML frontmatter (must start and end with '---').")
    else:
        if "name" not in fm_data or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", fm_data["name"]):
            errors.append("Frontmatter MUST include a lowercase kebab-case 'name' field.")
        elif skill_dir.name != fm_data["name"] and skill_dir.name not in ("skills", ""):
            errors.append(
                f"Directory name '{skill_dir.name}' MUST match frontmatter name '{fm_data['name']}'."
            )

        desc = fm_data.get("description", "").strip()
        if not desc:
            errors.append("Frontmatter MUST include a non-empty 'description' field.")
        else:
            word_count = len(desc.split())
            if word_count > 80:
                warnings.append(
                    f"Frontmatter description has {word_count} words (budget is < 80 words). Truncate to conserve startup tokens."
                )

    # Hedge terms audit
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    body = content[fm_match.end() :] if fm_match else content

    # Strip code blocks and inline code
    body_no_code = re.sub(r"```[\s\S]*?```", "", body)
    body_no_code = re.sub(r"`[^`]*`", "", body_no_code)

    for line_idx, line in enumerate(body_no_code.splitlines(), start=1):
        clean_line = line.strip().lower()
        # Ignore lines defining banned phrase rules or exclusions
        if any(marker in clean_line for marker in ["banned hedge", "forbidden", "hedge phrase", "must never use"]):
            continue
        for pattern in BANNED_HEDGE_PATTERNS:
            match = pattern.search(line)
            if match:
                warnings.append(
                    f"Line {line_idx}: Detected non-imperative hedge term '{match.group(0)}'. Directives MUST use MUST/NEVER/ALWAYS."
                )

    # Line count / token efficiency audit
    lines = content.splitlines()
    if len(lines) > 200:
        warnings.append(f"SKILL.md length ({len(lines)} lines) exceeds recommended 200-line limit. Move deep docs to references/.")

    # Script executable bit and symlink safety check
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for script_file in scripts_dir.iterdir():
            if script_file.is_symlink():
                resolved = script_file.resolve()
                if not str(resolved).startswith(str(skill_dir.resolve())):
                    warnings.append(f"Symlink '{script_file.name}' escapes skill directory boundary.")
            if script_file.is_file() and script_file.suffix in (".sh", ".py", ".bash"):
                if not os.access(script_file, os.X_OK):
                    warnings.append(f"Script '{script_file.name}' is not marked executable. Run `chmod +x {script_file}`.")

    print(f"--- Skill Audit: {skill_file} ---")
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  [ERROR] {err}")
    else:
        print("PASSED schema validation.")

    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")

    return len(errors) == 0


def list_skills(scope: str) -> None:
    targets: List[Tuple[str, Path]] = []
    if scope in ("workspace", "all"):
        root = find_workspace_root()
        ws_skills = root / ".agents" / "skills"
        if ws_skills.exists():
            targets.append(("workspace", ws_skills))
    if scope in ("global", "all"):
        gl_skills = Path.home() / ".gemini" / "config" / "skills"
        if gl_skills.exists():
            targets.append(("global", gl_skills))

    found = 0
    for label, base_dir in targets:
        print(f"=== {label.upper()} SKILLS ({base_dir}) ===")
        if not base_dir.is_dir():
            print("  (directory does not exist)")
            continue
        skill_dirs = [p for p in base_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
        if not skill_dirs:
            print("  (no skills found)")
            continue
        for s in sorted(skill_dirs, key=lambda p: p.name):
            found += 1
            try:
                raw_text = (s / "SKILL.md").read_text(encoding="utf-8")
                _, fm_data = parse_frontmatter(raw_text)
                desc = (fm_data or {}).get("description", "No description")
            except (OSError, UnicodeDecodeError):
                desc = "[Unreadable SKILL.md]"
            print(f"  • {s.name}: {desc[:90]}...")
    if found == 0:
        print("No skills discovered.")


def main():
    parser = argparse.ArgumentParser(description="Skill Scaffolder, Validator, and Inspector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scaffold command
    scaffold_parser = subparsers.add_parser("scaffold", help="Scaffold a new skill directory")
    scaffold_parser.add_argument("--name", required=True, help="Lowercase kebab-case skill identifier")
    scaffold_parser.add_argument("--description", required=True, help="Detailed trigger description for Tier-1 discovery")
    scaffold_parser.add_argument(
        "--scope",
        choices=["workspace", "global"],
        default="workspace",
        help="Target scope: 'workspace' (.agents/skills) or 'global' (~/.gemini/config/skills)",
    )
    scaffold_parser.add_argument("--target-dir", help="Explicit parent directory for the skill")
    scaffold_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing skill files")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate an existing skill for schema and directives")
    validate_parser.add_argument("path", help="Path to skill directory or SKILL.md file")

    # List command
    list_parser = subparsers.add_parser("list", help="List discovered skills")
    list_parser.add_argument(
        "--scope",
        choices=["workspace", "global", "all"],
        default="all",
        help="Filter scope by workspace, global, or all",
    )

    args = parser.parse_args()

    if args.command == "scaffold":
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", args.name):
            print(f"Error: Skill name '{args.name}' must be lowercase kebab-case.", file=sys.stderr)
            sys.exit(1)

        if args.target_dir:
            dest = Path(args.target_dir).expanduser().resolve()
        elif args.scope == "global":
            dest = Path.home() / ".gemini" / "config" / "skills"
        else:
            dest = find_workspace_root() / ".agents" / "skills"

        scaffold_skill(args.name, args.description, dest, overwrite=args.overwrite)

    elif args.command == "validate":
        ok = validate_skill(Path(args.path).expanduser().resolve())
        sys.exit(0) if ok else sys.exit(1)

    elif args.command == "list":
        list_skills(args.scope)


if __name__ == "__main__":
    main()
