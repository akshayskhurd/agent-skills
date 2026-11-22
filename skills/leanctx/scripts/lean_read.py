#!/usr/bin/env python3
"""
Universal file reader for leanctx across any harness (Claude Code, OpenCode, Pi, Antigravity).
Safely reads files with line-budget clamping, streaming islice, per-line character capping,
and total byte limits to prevent token-bomb context explosions.
"""
import argparse
import itertools
import os
import sys

MAX_CHARS_PER_LINE = 500
MAX_TOTAL_BYTES = 24 * 1024  # 24 KB hard ceiling


def main():
    parser = argparse.ArgumentParser(description="Universal safe file reader with line and byte budget clamping")
    parser.add_argument("path", help="Path to file to read")
    parser.add_argument("--start", "-s", type=int, default=1, help="1-indexed start line (default: 1)")
    parser.add_argument("--end", "-e", type=int, default=None, help="1-indexed end line (inclusive)")
    parser.add_argument("--max", "-m", type=int, default=150, help="Maximum allowed lines to return (default: 150)")

    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: Path does not exist or is not a regular file: {args.path}", file=sys.stderr)
        sys.exit(1)

    start_idx = max(1, args.start) - 1
    max_to_fetch = args.max
    if args.end is not None and args.end >= args.start:
        max_to_fetch = min(args.max, args.end - args.start + 1)

    selected_lines = []
    total_scanned = 0
    total_bytes = 0
    hit_byte_limit = False

    try:
        with open(args.path, "r", encoding="utf-8", errors="replace") as f:
            # Stream directly using islice to prevent memory explosion on multi-GB files
            stream = itertools.islice(f, start_idx, start_idx + max_to_fetch + 1)
            for line in stream:
                total_scanned += 1
                if total_scanned > max_to_fetch:
                    break
                # Per-line character cap to block minified single-line token bombs
                if len(line) > MAX_CHARS_PER_LINE:
                    line = line[:MAX_CHARS_PER_LINE] + " [...line truncated]\n"
                line_bytes = len(line.encode("utf-8"))
                if total_bytes + line_bytes > MAX_TOTAL_BYTES:
                    hit_byte_limit = True
                    break
                selected_lines.append(line)
                total_bytes += line_bytes
    except Exception as exc:
        print(f"Error reading file '{args.path}': {str(exc)}", file=sys.stderr)
        sys.exit(1)

    actual_count = len(selected_lines)
    header = f"[leanctx: Reading '{args.path}' lines {start_idx + 1} to {start_idx + actual_count}]\n"
    if total_scanned > max_to_fetch:
        header = f"[leanctx: File '{args.path}' clamped to {max_to_fetch} lines]\n"
    elif hit_byte_limit:
        header = f"[leanctx: File '{args.path}' clamped to {MAX_TOTAL_BYTES // 1024} KB byte budget]\n"

    sys.stdout.write(header)
    sys.stdout.write("".join(selected_lines))
    if total_scanned > max_to_fetch or hit_byte_limit:
        sys.stdout.write(f"\n[leanctx: Notice: Additional lines truncated to preserve context. Use targeted --start and --end]\n")


if __name__ == "__main__":
    main()
