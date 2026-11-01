#!/usr/bin/env python3
"""Universal Installer and Harness Provisioner for Agent Skills.

Enforces zero manual copying. Installs, symlinks, audits, and uninstalls skills
across Claude Code, OpenCode, Codex, Pi, Google Antigravity/Gemini, and Universal Agents.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Supported harness registry mapping
HARNESS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "claude": {
        "name": "Claude Code",
        "home_markers": [".claude"],
        "global_dir": Path("~/.claude/skills").expanduser(),
        "local_dir": Path(".claude/skills"),
    },
    "opencode": {
        "name": "OpenCode",
        "home_markers": [".opencode", ".config/opencode"],
        "global_dir": Path("~/.opencode/skills").expanduser(),
        "local_dir": Path(".opencode/skills"),
    },
    "codex": {
        "name": "Codex / OpenAI",
        "home_markers": [".codex"],
        "global_dir": Path("~/.codex/skills").expanduser(),
        "local_dir": Path(".codex/skills"),
    },
    "pi": {
        "name": "Pi Agent",
        "home_markers": [".pi"],
        "global_dir": Path("~/.pi/skills").expanduser(),
        "local_dir": Path(".pi/skills"),
    },
    "gemini": {
        "name": "Google Antigravity / Gemini CLI",
        "home_markers": [".gemini"],
        "global_dir": Path("~/.gemini/config/skills").expanduser(),
        "local_dir": Path(".gemini/skills"),
    },
    "antigravity": {
        "name": "Google Antigravity / Gemini CLI",
        "home_markers": [".gemini"],
        "global_dir": Path("~/.gemini/config/skills").expanduser(),
        "local_dir": Path(".gemini/skills"),
    },
    "agents": {
        "name": "Universal Agent Skills Standard",
        "home_markers": [".agents"],
        "global_dir": Path("~/.agents/skills").expanduser(),
        "local_dir": Path(".agents/skills"),
    },
}

ROOT_DIR = Path(__file__).resolve().parent
SKILLS_SRC_DIR = ROOT_DIR / "skills"


def discover_source_skills() -> List[str]:
    """Scan and return all valid skill folder names from the repository."""
    if not SKILLS_SRC_DIR.is_dir():
        return []
    valid = []
    for item in sorted(SKILLS_SRC_DIR.iterdir()):
        if item.is_dir() and (item / "SKILL.md").is_file():
            valid.append(item.name)
    return valid


def detect_installed_harnesses(home_dir: Optional[Path] = None) -> List[str]:
    """Detect available agent harnesses installed on the host system."""
    home = home_dir or Path.home()
    detected: Set[str] = set()

    canonical_targets = ["claude", "opencode", "codex", "pi", "gemini", "agents"]
    for key in canonical_targets:
        meta = HARNESS_REGISTRY[key]
        for marker in meta["home_markers"]:
            target_marker = home / marker
            if target_marker.exists():
                detected.add(key)
                break

    # If nothing detected, fallback to standard universal agents
    if not detected:
        detected.add("agents")

    return sorted(list(detected))


def resolve_target_directories(
    targets: List[str],
    is_global: bool = True,
    custom_dest: Optional[str] = None,
    home_dir: Optional[Path] = None,
) -> List[Tuple[str, Path]]:
    """Resolve target output directories for selected harnesses."""
    if custom_dest:
        dest_path = Path(custom_dest).expanduser().resolve()
        return [("custom", dest_path)]

    resolved = []
    seen_paths: Set[Path] = set()
    home = home_dir or Path.home()

    for t in targets:
        key = t.strip().lower()
        if key not in HARNESS_REGISTRY:
            raise ValueError(f"Unknown agent harness: '{key}'. Choose from: {sorted(list(HARNESS_REGISTRY.keys()))}")

        meta = HARNESS_REGISTRY[key]
        if is_global:
            if home_dir:
                # Custom home substitution for isolated unit testing
                if key in ("gemini", "antigravity"):
                    out_dir = home / ".gemini" / "config" / "skills"
                elif key == "agents":
                    out_dir = home / ".agents" / "skills"
                elif key == "opencode":
                    out_dir = home / ".opencode" / "skills"
                else:
                    out_dir = home / f".{key}" / "skills"
            else:
                out_dir = meta["global_dir"]
        else:
            out_dir = Path.cwd() / meta["local_dir"]

        if out_dir not in seen_paths:
            seen_paths.add(out_dir)
            resolved.append((key, out_dir))

    return resolved


def install_skills(
    skills_to_install: List[str],
    target_dirs: List[Tuple[str, Path]],
    symlink: bool = False,
    dry_run: bool = False,
) -> int:
    """Deploy skills to target harness directories via copy or symlink."""
    success_count = 0
    available = discover_source_skills()

    for s in skills_to_install:
        if s not in available:
            print(f"Error: Skill '{s}' does not exist in source repository.", file=sys.stderr)
            return 1

    for harness_key, dest_dir in target_dirs:
        harness_name = HARNESS_REGISTRY.get(harness_key, {}).get("name", harness_key.capitalize())
        print(f"\n📂 Provisioning Harness: {harness_name} -> {dest_dir}")

        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        for skill_name in skills_to_install:
            src = SKILLS_SRC_DIR / skill_name
            dest = dest_dir / skill_name

            action_desc = "Symlinking" if symlink else "Installing"
            print(f"  • {action_desc} skill '{skill_name}'... ", end="")

            if dry_run:
                print("[DRY-RUN]")
                continue

            try:
                # Remove existing skill path if present
                if dest.is_symlink() or dest.is_file():
                    dest.unlink()
                elif dest.is_dir():
                    shutil.rmtree(dest)

                if symlink:
                    try:
                        dest.symlink_to(src.resolve(), target_is_directory=True)
                    except OSError:
                        # Fallback to copy when symlink privileges are unheld (e.g. Windows unprivileged)
                        shutil.copytree(src, dest)
                else:
                    shutil.copytree(src, dest)

                print("DONE")
                success_count += 1
            except OSError as err:
                print(f"FAILED ({err})", file=sys.stderr)
                return 1

    return 0


def uninstall_skills(
    skills_to_remove: List[str],
    target_dirs: List[Tuple[str, Path]],
    dry_run: bool = False,
) -> int:
    """Remove deployed skills from target harness directories."""
    for harness_key, dest_dir in target_dirs:
        harness_name = HARNESS_REGISTRY.get(harness_key, {}).get("name", harness_key.capitalize())
        print(f"\n🗑️  Cleaning Harness: {harness_name} -> {dest_dir}")

        if not dest_dir.exists():
            print("  Directory does not exist. Skipping.")
            continue

        for skill_name in skills_to_remove:
            target = dest_dir / skill_name
            if not (target.exists() or target.is_symlink()):
                print(f"  • Skill '{skill_name}' not present.")
                continue

            print(f"  • Removing '{skill_name}'... ", end="")
            if dry_run:
                print("[DRY-RUN]")
                continue

            try:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target)
                print("REMOVED")
            except OSError as err:
                print(f"FAILED ({err})", file=sys.stderr)
                return 1

    return 0


def report_status(target_dirs: List[Tuple[str, Path]]) -> None:
    """Audit and report installed skills status across all harnesses."""
    available = discover_source_skills()
    print("\n================================================================")
    print("📊 AGENT SKILLS HARNESS STATUS AUDIT")
    print("================================================================")
    print(f"Source repository skills ({len(available)}): {', '.join(available)}\n")

    for harness_key, dest_dir in target_dirs:
        harness_name = HARNESS_REGISTRY.get(harness_key, {}).get("name", harness_key.capitalize())
        print(f"🔍 Harness: {harness_name}")
        print(f"   Directory: {dest_dir}")

        if not dest_dir.exists():
            print("   Status: Directory does not exist (not provisioned).\n")
            continue

        installed = []
        for s in available:
            skill_path = dest_dir / s
            if skill_path.exists() or skill_path.is_symlink():
                link_flag = " (symlinked)" if skill_path.is_symlink() else ""
                installed.append(f"{s}{link_flag}")

        if installed:
            print(f"   Installed skills ({len(installed)}):")
            for item in installed:
                print(f"     ✓ {item}")
        else:
            print("   No skills currently installed in this harness.")
        print()


def main() -> int:
    """CLI Entry point for universal skill installation."""
    parser = argparse.ArgumentParser(
        description="Universal Agent Skills Installer for Claude, OpenCode, Codex, Pi, Antigravity/Gemini, and Agents."
    )
    parser.add_argument(
        "--target",
        "-t",
        default="auto",
        help="Target harness: 'auto' (detect installed), 'all', or comma-separated list (claude, opencode, codex, pi, gemini, agents).",
    )
    parser.add_argument(
        "--skills",
        "-s",
        default="all",
        help="Comma-separated skills to install, or 'all' (default: all).",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["copy", "symlink"],
        default="copy",
        help="Installation method: 'copy' for standalone deployment, 'symlink' for live git repository sync.",
    )
    parser.add_argument(
        "--global",
        "-g",
        dest="is_global",
        action="store_true",
        default=True,
        help="Install to user global home directories (default).",
    )
    parser.add_argument(
        "--local",
        "-l",
        dest="is_local",
        action="store_true",
        default=False,
        help="Install to current project/workspace directory instead of user home.",
    )
    parser.add_argument(
        "--dest",
        "-d",
        default=None,
        help="Install to a specific custom directory path.",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Shortcut flag for --mode symlink.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall specified skills from the target harnesses.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Audit and display skill status across targeted harnesses.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all skills available in this repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview installation actions without writing changes to disk.",
    )

    args = parser.parse_args()

    available_skills = discover_source_skills()
    if args.list:
        print("\nAvailable Agent Skills:")
        for s in available_skills:
            print(f"  • {s}")
        print("\nSupported Target Harnesses:")
        for key in ["claude", "opencode", "codex", "pi", "gemini", "agents"]:
            meta = HARNESS_REGISTRY[key]
            print(f"  • {key.ljust(12)} -> {meta['name']} ({meta['global_dir']})")
        return 0

    # Determine skills subset
    if args.skills.strip().lower() == "all":
        selected_skills = available_skills
    else:
        selected_skills = [x.strip() for x in args.skills.split(",") if x.strip()]

    # Determine target harnesses
    target_arg = args.target.strip().lower()
    canonical_list = ["claude", "opencode", "codex", "pi", "gemini", "agents"]

    if target_arg == "all":
        target_keys = canonical_list
    elif target_arg == "auto":
        target_keys = detect_installed_harnesses()
        print(f"⚡ Auto-detected installed harnesses: {', '.join(target_keys)}")
    else:
        target_keys = [x.strip() for x in target_arg.split(",") if x.strip()]

    is_global = not args.is_local
    use_symlink = args.symlink or (args.mode == "symlink")

    try:
        resolved_dirs = resolve_target_directories(
            targets=target_keys,
            is_global=is_global,
            custom_dest=args.dest,
        )
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    if args.status:
        report_status(resolved_dirs)
        return 0

    if args.uninstall:
        return uninstall_skills(selected_skills, resolved_dirs, dry_run=args.dry_run)

    return install_skills(
        skills_to_install=selected_skills,
        target_dirs=resolved_dirs,
        symlink=use_symlink,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
