#!/usr/bin/env python3
"""
Telemetry and Token Estimator for leanctx.
Computes BPE token approximations (~3.85 chars/token for code/JSON),
evaluates context watermarks, calculates Signal-to-Noise Ratio (SNR),
and estimates cumulative cost deltas.
"""
import argparse
import json
import os
import sys
from typing import Dict, Any

# Standard BPE character-to-token ratio heuristic for mixed code and natural language
CHARS_PER_TOKEN = 3.85


def estimate_tokens(text: str) -> int:
    """Return estimated token count for given text string."""
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def evaluate_snr(rank1_3_text: str, total_text: str) -> float:
    """Calculate Signal-to-Noise Ratio (SNR) as percentage of Ranks 1-3 vs total tokens."""
    total_tokens = estimate_tokens(total_text)
    if total_tokens == 0:
        return 100.0
    signal_tokens = estimate_tokens(rank1_3_text)
    return min(100.0, round((signal_tokens / total_tokens) * 100.0, 2))


def estimate_cost(input_tokens: int, output_tokens: int, rate_in_per_m: float = 3.0, rate_out_per_m: float = 15.0) -> float:
    """Calculate dollar cost against standard provider rates per million tokens."""
    cost_in = (input_tokens / 1_000_000.0) * rate_in_per_m
    cost_out = (output_tokens / 1_000_000.0) * rate_out_per_m
    return round(cost_in + cost_out, 6)


def main():
    parser = argparse.ArgumentParser(description="leanctx Telemetry & Token Cost Calculator")
    parser.add_argument("--file", "-f", help="Evaluate tokens in file")
    parser.add_argument("--text", "-t", help="Evaluate tokens in string")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("SIGNAL_FILE", "TOTAL_FILE"), help="Compare signal vs total file for SNR calculation")

    args = parser.parse_args()

    if args.compare:
        sig_path, tot_path = args.compare
        with open(sig_path, "r", encoding="utf-8", errors="replace") as sf:
            sig_text = sf.read()
        with open(tot_path, "r", encoding="utf-8", errors="replace") as tf:
            tot_text = tf.read()

        sig_tok = estimate_tokens(sig_text)
        tot_tok = estimate_tokens(tot_text)
        snr = evaluate_snr(sig_text, tot_text)
        print(json.dumps({
            "signal_tokens": sig_tok,
            "total_tokens": tot_tok,
            "snr_percentage": snr
        }, indent=2))
        return

    text = ""
    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    tokens = estimate_tokens(text)
    cost = estimate_cost(tokens, 0)
    print(json.dumps({
        "characters": len(text),
        "estimated_tokens": tokens,
        "estimated_cost_usd": cost
    }, indent=2))


if __name__ == "__main__":
    main()
