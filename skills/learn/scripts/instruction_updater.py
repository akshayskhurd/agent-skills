#!/usr/bin/env python3
"""
Instruction Updater Helper Script for Antigravity

Manages, deduplicates, and surgically updates agent instruction files:
- Global instructions: ~/.gemini/GEMINI.md
- Workspace instructions: <workspace>/GEMINI.md or AGENTS.md
- Ensures rules stay categorized, crisp, non-contradictory, and within the 24KB limit.
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

MAX_RULE_FILE_BYTES = 24000  # Antigravity 24KB per-file cap


def resolve_default_file(path: Optional[str]) -> str:
    if path:
        return os.path.abspath(os.path.expanduser(path))
    # Default to global instructions
    return os.path.expanduser("~/.gemini/GEMINI.md")


def load_instructions(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def save_instructions(file_path: str, content: str) -> None:
    encoded_len = len(content.encode("utf-8"))
    if encoded_len > MAX_RULE_FILE_BYTES:
        raise ValueError(
            f"Content size ({encoded_len} bytes) exceeds the Antigravity 24KB limit ({MAX_RULE_FILE_BYTES} bytes)."
        )
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_sections(content: str) -> Dict[str, List[str]]:
    """Parse markdown headers (## Category) and their bullet points."""
    sections: Dict[str, List[str]] = {}
    current_section = "General Directives"
    sections[current_section] = []

    lines = content.splitlines()
    for line in lines:
        header_match = re.match(r"^##+\s+(.+)$", line.strip())
        if header_match:
            current_section = header_match.group(1).strip()
            if current_section not in sections:
                sections[current_section] = []
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            sections[current_section].append(line.strip())

    return sections


def rule_similarity(rule_a: str, rule_b: str) -> float:
    """Compute simple word Jaccard similarity to detect duplicates."""
    words_a = set(re.findall(r"\w{4,}", rule_a.lower()))
    words_b = set(re.findall(r"\w{4,}", rule_b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def format_rule_entry(directive: str, rationale: Optional[str] = None) -> str:
    clean_dir = directive.strip().lstrip("-* \t")
    if rationale and rationale.strip():
        clean_rat = rationale.strip().lstrip("-* \t")
        return f"- **{clean_dir}**\n  *Rationale*: {clean_rat}"
    return f"- {clean_dir}"


def add_or_update_rule(
    file_path: str,
    category: str,
    directive: str,
    rationale: Optional[str] = None
) -> Tuple[bool, str]:
    """Adds a rule or updates an existing similar rule under the given category."""
    content = load_instructions(file_path)
    new_entry = format_rule_entry(directive, rationale)

    # Check for near-duplicate existing rule
    existing_lines = content.splitlines()
    for idx, line in enumerate(existing_lines):
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            sim = rule_similarity(line, directive)
            if sim > 0.65:
                # Replace the existing rule
                existing_lines[idx] = new_entry
                updated_content = "\n".join(existing_lines).strip() + "\n"
                save_instructions(file_path, updated_content)
                return True, f"Updated existing similar rule in '{file_path}':\n  Old: {line.strip()}\n  New: {new_entry}"

    # If category exists, append under it; otherwise append new category
    category_header = f"## {category}"
    if category_header in content:
        # Insert right under the category header
        pattern = re.escape(category_header) + r"\n+"
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            updated_content = content[:insert_pos] + new_entry + "\n\n" + content[insert_pos:]
        else:
            updated_content = content.rstrip() + f"\n\n{new_entry}\n"
    else:
        # Append new category section
        prefix = "\n\n" if content.strip() else ""
        if not content.strip():
            header = "# Agent Instructions & Persistent Learnings\n\n"
        else:
            header = ""
        updated_content = (
            content.rstrip() + prefix + header + f"{category_header}\n\n{new_entry}\n"
        )

    # Clean double blank lines
    updated_content = re.sub(r"\n{3,}", "\n\n", updated_content).strip() + "\n"
    save_instructions(file_path, updated_content)
    return True, f"Added new rule under '[{category}]' in '{file_path}':\n  {new_entry}"


def list_rules(file_path: str) -> None:
    content = load_instructions(file_path)
    if not content.strip():
        print(f"No instructions found in {file_path}")
        return
    print(f"--- Agent Instructions: {file_path} ---")
    sections = parse_sections(content)
    for sec, rules in sections.items():
        if rules:
            print(f"\n[{sec}]")
            for r in rules:
                print(f"  {r}")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Instruction Updater")
    parser.add_argument("--file", "-f", help="Target instruction file path (default: ~/.gemini/GEMINI.md)")
    parser.add_argument("--category", "-c", default="General Directives", help="Rule category heading")
    parser.add_argument("--rule", "-r", help="Directive to remember (e.g. 'ALWAYS use pytest -vv')")
    parser.add_argument("--rationale", help="Optional context or reason for this instruction")
    parser.add_argument("--list", "-l", action="store_true", help="List active instructions")

    args = parser.parse_args()
    file_path = resolve_default_file(args.file)

    if args.list:
        list_rules(file_path)
        sys.exit(0)

    if not args.rule:
        parser.print_help()
        sys.exit(1)

    try:
        success, msg = add_or_update_rule(
            file_path=file_path,
            category=args.category,
            directive=args.rule,
            rationale=args.rationale
        )
        print(msg)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
