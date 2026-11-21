#!/usr/bin/env python3
"""
Universal file reader for leanctx across any harness (Claude Code, OpenCode, Pi, Antigravity).
Safely reads files with line-budget clamping to prevent unconstrained token explosion.
"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Universal safe file reader with line budget clamping")
    parser.add_argument("path", help="Path to file to read")
    parser.add_argument("--start", "-s", type=int, default=1, help="1-indexed start line (default: 1)")
    parser.add_argument("--end", "-e", type=int, default=None, help="1-indexed end line (inclusive)")
    parser.add_argument("--max", "-m", type=int, default=150, help="Maximum allowed lines to return (default: 150)")

    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: Path does not exist or is not a regular file: {args.path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as exc:
        print(f"Error reading file '{args.path}': {str(exc)}", file=sys.stderr)
        sys.exit(1)

    total_lines = len(all_lines)
    start_idx = max(1, args.start) - 1
    end_idx = args.end if args.end is not None else total_lines

    selected = all_lines[start_idx:end_idx]

    if len(selected) > args.max:
        clamped = selected[:args.max]
        sys.stdout.write(f"[leanctx: File '{args.path}' ({total_lines} total lines) clamped to {args.max} lines]\n")
        sys.stdout.write("".join(clamped))
        sys.stdout.write(f"\n[leanctx: Notice: {len(selected) - args.max} additional requested lines truncated. Use targeted --start and --end]\n")
    else:
        sys.stdout.write(f"[leanctx: Reading '{args.path}' lines {start_idx + 1} to {min(end_idx, total_lines)} of {total_lines}]\n")
        sys.stdout.write("".join(selected))


if __name__ == "__main__":
    main()
