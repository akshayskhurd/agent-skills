#!/usr/bin/env python3
"""
Grill Verification & Quality Gate Helper Script

Automates static heuristics for the Grill Skill:
- Scans for banned non-imperative hedge phrases (enforcing MUST/NEVER/ALWAYS clarity)
- Detects critical security, reliability, and architectural anti-patterns
- Recursively audits directories or individual files
- Validates cross-language semantic contract preservation (Python, JS/TS, Go, Rust, Java)
- Emits human-readable or structured JSON reports
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

# Pre-compiled regex patterns for banned hedge phrases
BANNED_HEDGE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bmight\b",
        r"\bmaybe\b",
        r"\bperhaps\b",
        r"\bcould consider\b",
        r"\bshould probably\b",
        r"\bseems to be\b",
        r"\blooks fine\b",
        r"\bseems ok\b",
        r"\bI think\b",
        r"\bit might be good\b",
        r"\bpotentially\b",
    ]
]

# Pre-compiled multi-language code anti-patterns
CODE_ANTI_PATTERNS = [
    (re.compile(r"except\s*:\s*(?:pass|continue)"), "Developer / SRE: Naked except swallowing errors silently"),
    (re.compile(r"except\s+Exception\s*:\s*pass"), "Developer / SRE: Blind Exception swallowing"),
    (re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "Developer / SRE: Empty catch block in JS/TS/Java"),
    (re.compile(r"shell\s*=\s*True"), "Security Researcher: Command injection risk with shell=True"),
    (re.compile(r"os\.system\("), "Security Researcher: Insecure system call execution via os.system"),
    (re.compile(r"subprocess\.(?:call|check_call|Popen)\([^)]*shell\s*=\s*True"), "Security Researcher: Subprocess invoked with shell=True"),
    (re.compile(r"eval\(|exec\("), "Security Researcher: Dangerous dynamic evaluation (eval/exec)"),
    (re.compile(r"pickle\.loads?\("), "Security Researcher: Insecure deserialization via pickle"),
    (re.compile(r"yaml\.unsafe_load\("), "Security Researcher: Insecure YAML loading via unsafe_load"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Security Researcher: Hardcoded AWS Access Key ID"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Security Researcher: Hardcoded Private Cryptographic Key"),
    (re.compile(r"(?:api_key|password|secret|token)\s*=\s*['\"][A-Za-z0-9_\-]{12,}['\"]", re.IGNORECASE), "Security Researcher: Potential hardcoded secret/credential"),
    (re.compile(r"requests\.(?:get|post|put|delete)\("), "SRE: Python requests call without explicit timeout"),
    (re.compile(r"urllib\.request\.urlopen\("), "SRE: Network call without explicit timeout"),
]

# Multi-language public symbol patterns
SYMBOL_PATTERNS = [
    # Python def/class
    re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    # JS/TS export function / class / const / interface / type
    re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|class|interface|type|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    # Go func / type
    re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    # Rust pub fn / pub struct / pub enum / pub trait
    re.compile(r"^pub\s+(?:async\s+)?(?:fn|struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
]


def is_binary_file(filepath: str) -> bool:
    """Check if file appears to be binary."""
    try:
        with open(filepath, "tr") as check_file:
            check_file.read(1024)
            return False
    except UnicodeDecodeError:
        return True


def check_hedges(content: str) -> List[Tuple[int, str, str]]:
    """Scan text for banned non-imperative hedge phrases."""
    issues = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        clean_line = re.sub(r"[\*_`\"']", "", line).lower()
        # Skip lines that define rule exclusions, regex patterns, or test assertions
        if any(marker in clean_line for marker in [
            "banned_", "must never use", "prohibit", "forbidden", "hedge phrase", "hedge words", "such as maybe",
            "re.compile", "re.search", "pattern"
        ]) or line.strip().startswith("r\"") or line.strip().startswith("r'"):
            continue
        for pattern in BANNED_HEDGE_PATTERNS:
            match = pattern.search(line)
            if match:
                issues.append((idx, f"Banned hedge phrase '{match.group(0)}'", line.strip()))
    return issues


def check_anti_patterns(content: str) -> List[Tuple[int, str, str]]:
    """Scan code content for critical security, reliability, and code defects."""
    issues = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # Skip pattern definitions or scanner logic itself
        trimmed = line.strip()
        if trimmed.startswith("re.compile") or "(re.compile(" in trimmed or trimmed.startswith("#") or "pattern" in trimmed:
            continue
        for pattern, desc in CODE_ANTI_PATTERNS:
            if pattern.search(line):
                # If checking for timeout, ignore if timeout argument is present
                if "without explicit timeout" in desc and "timeout" in line:
                    continue
                issues.append((idx, desc, line.strip()))
    return issues


def extract_symbols(content: str) -> Set[str]:
    """Extract declared symbols across multiple programming languages."""
    symbols = set()
    for pattern in SYMBOL_PATTERNS:
        matches = pattern.findall(content)
        symbols.update(matches)
    return symbols


def compare_semantics(orig_content: str, fixed_content: str) -> List[str]:
    """Verify that all public function, method, and type definitions remain intact."""
    warnings = []
    orig_defs = extract_symbols(orig_content)
    fixed_defs = extract_symbols(fixed_content)

    missing = orig_defs - fixed_defs
    if missing:
        for symbol in sorted(missing):
            warnings.append(f"SEMANTIC BREAK RISK: Symbol '{symbol}' existed in original but is missing in remediated artifact!")
    return warnings


def audit_single_file(file_path: str, orig_path: str = None) -> Dict:
    """Run full Grill audit on a single file."""
    if not os.path.isfile(file_path):
        return {"error": f"Path is not a regular file: {file_path}", "passed": False}

    if is_binary_file(file_path):
        return {"file": file_path, "skipped": "Binary file skipped", "passed": True}

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    total_lines = len(lines)
    hedge_issues = check_hedges(content)

    code_extensions = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp")
    is_code = file_path.endswith(code_extensions)
    anti_patterns = check_anti_patterns(content) if is_code else []

    semantic_warnings = []
    if orig_path and os.path.isfile(orig_path):
        with open(orig_path, "r", encoding="utf-8", errors="replace") as orig_f:
            orig_content = orig_f.read()
        semantic_warnings = compare_semantics(orig_content, content)

    passed = len(hedge_issues) == 0 and len(anti_patterns) == 0 and len(semantic_warnings) == 0

    return {
        "file": file_path,
        "total_lines": total_lines,
        "is_code": is_code,
        "hedge_issues": [{"line": l, "msg": m, "snippet": s} for l, m, s in hedge_issues],
        "anti_patterns": [{"line": l, "msg": m, "snippet": s} for l, m, s in anti_patterns],
        "semantic_warnings": semantic_warnings,
        "passed": passed,
    }


def collect_target_files(target_path: str) -> List[str]:
    """Return list of files to inspect (either single file or recursive walk)."""
    if os.path.isfile(target_path):
        return [target_path]
    
    target_files = []
    ignored_dirs = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv"}
    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in sorted(files):
            full_path = os.path.join(root, f)
            if not is_binary_file(full_path):
                target_files.append(full_path)
    return target_files


def main():
    parser = argparse.ArgumentParser(description="Grill Quality Gate & Verification Checker")
    parser.add_argument("--file", "-f", required=True, help="Target file or directory to audit")
    parser.add_argument("--original", "-o", help="Original file path for semantic invariance comparison")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: Target path '{args.file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    files_to_audit = collect_target_files(args.file)
    if not files_to_audit:
        print(f"WARNING: No text files found to audit at '{args.file}'.", file=sys.stderr)
        sys.exit(0)

    results = []
    all_passed = True
    total_lines_interrogated = 0

    for path in files_to_audit:
        orig = args.original if len(files_to_audit) == 1 else None
        res = audit_single_file(path, orig)
        results.append(res)
        total_lines_interrogated += res.get("total_lines", 0)
        if not res.get("passed", False):
            all_passed = False

    if args.json:
        print(json.dumps({
            "target": args.file,
            "total_files": len(files_to_audit),
            "total_lines": total_lines_interrogated,
            "all_passed": all_passed,
            "results": results
        }, indent=2))
        sys.exit(0 if all_passed else 1)

    # Human-readable output
    print("=" * 64)
    print(f"🔥 GRILL QUALITY GATE AUDIT")
    print(f"   Target Path: {args.file}")
    print(f"   Files Scanned: {len(files_to_audit)}")
    print(f"   Total Lines Interrogated: {total_lines_interrogated}")
    print("=" * 64)

    for res in results:
        fpath = res["file"]
        if res["passed"]:
            print(f"✅ {fpath} (Lines: {res['total_lines']}) — ZERO DEFECTS")
        else:
            print(f"\n❌ DEFECTS DETECTED: {fpath}")
            for issue in res["hedge_issues"]:
                print(f"   Line {issue['line']:4d} | [HEDGE] {issue['msg']} -> '{issue['snippet']}'")
            for pattern in res["anti_patterns"]:
                print(f"   Line {pattern['line']:4d} | [ANTI-PATTERN] {pattern['msg']} -> '{pattern['snippet']}'")
            for warn in res["semantic_warnings"]:
                print(f"   [SEMANTIC] {warn}")

    print("-" * 64)
    if all_passed:
        print("🌟 ALL TARGETS CERTIFIED ZERO-DEFECT. Quality gate passed.")
        sys.exit(0)
    else:
        print("🔥 GRILL RESULT: FAILED. Remediation required.")
        sys.exit(1)


if __name__ == "__main__":
    main()
