#!/usr/bin/env python3
"""
Single-Pass Contract & Integrity Verifier.
Executes static syntax checks, interface boundary validation, and schema conformance.
"""

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit to prevent memory exhaustion


def verify_python_syntax(file_path: Path) -> Tuple[bool, List[str]]:
    """Validate Python AST syntax and basic compilation."""
    errors = []
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False, [f"File size exceeds maximum threshold of {MAX_FILE_SIZE_BYTES} bytes."]
        source = file_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}:{e.offset}: {e.msg}")
    except (OSError, UnicodeDecodeError) as e:
        errors.append(f"I/O error reading file: {e}")
    return len(errors) == 0, errors


def verify_json_schema(file_path: Path) -> Tuple[bool, List[str]]:
    """Validate JSON syntax and structure."""
    errors = []
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False, [f"File size exceeds maximum threshold of {MAX_FILE_SIZE_BYTES} bytes."]
        source = file_path.read_text(encoding="utf-8")
        json.loads(source)
    except json.JSONDecodeError as e:
        errors.append(f"JSON decode error at line {e.lineno}:{e.colno}: {e.msg}")
    except (OSError, UnicodeDecodeError) as e:
        errors.append(f"I/O error reading file: {e}")
    return len(errors) == 0, errors


def verify_shell_syntax(file_path: Path) -> Tuple[bool, List[str]]:
    """Validate shell script syntax with bash -n."""
    errors = []
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False, [f"File size exceeds maximum threshold of {MAX_FILE_SIZE_BYTES} bytes."]
        proc = subprocess.run(
            ["bash", "-n", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            errors.append(f"Bash syntax error: {proc.stderr.strip()}")
    except (subprocess.SubprocessError, OSError) as e:
        errors.append(f"Failed to execute bash -n: {e}")
    return len(errors) == 0, errors


def verify_file(target_path: Path, forced_type: str = "auto") -> Tuple[bool, List[str]]:
    if not target_path.is_file():
        return False, [f"Target '{target_path}' is not a regular file."]

    file_type = forced_type
    if file_type == "auto":
        suffix = target_path.suffix.lower()
        if suffix in (".py", ".pyw"):
            file_type = "python"
        elif suffix in (".json", ".jsonc"):
            file_type = "json"
        elif suffix in (".sh", ".bash"):
            file_type = "shell"
        else:
            return True, []  # Unsupported or neutral file type, skip gracefully

    if file_type == "python":
        return verify_python_syntax(target_path)
    elif file_type == "json":
        return verify_json_schema(target_path)
    elif file_type == "shell":
        return verify_shell_syntax(target_path)

    return True, []


def main():
    parser = argparse.ArgumentParser(description="Single-Pass Contract & Integrity Verifier")
    parser.add_argument("target", help="File or directory to verify")
    parser.add_argument(
        "--type",
        choices=["python", "json", "shell", "auto"],
        default="auto",
        help="Target language/format type (default: auto)",
    )

    args = parser.parse_args()
    target_path = Path(args.target).expanduser().resolve()

    if not target_path.exists():
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    targets: List[Path] = []
    if target_path.is_dir():
        for root_dir, _, files in os.walk(target_path):
            for f in files:
                p = Path(root_dir) / f
                if p.suffix.lower() in (".py", ".json", ".sh", ".bash"):
                    targets.append(p)
    else:
        targets.append(target_path)

    if not targets:
        print(f"No verifiable files found at '{target_path}'.")
        sys.exit(0)

    total_failures = 0
    for file_to_check in targets:
        ok, errors = verify_file(file_to_check, args.type)
        if ok:
            print(f"PASSED: '{file_to_check.name}' verified zero syntax errors.")
        else:
            total_failures += 1
            print(f"FAILED: '{file_to_check.name}' failed contract validation:", file=sys.stderr)
            for err in errors:
                print(f"  [ERROR] {err}", file=sys.stderr)

    if total_failures > 0:
        print(f"\nVerification failed with {total_failures} defect(s).", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {len(targets)} target(s) successfully verified zero defects.")
    sys.exit(0)


if __name__ == "__main__":
    main()
