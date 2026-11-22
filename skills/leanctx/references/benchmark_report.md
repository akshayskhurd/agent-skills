# Empirical Benchmark Report: `leanctx` vs Baseline

**Evaluation Scope:** 10 Real-World Software Engineering Scenarios + 25-Turn Multi-Phase Simulation  
**Harness Workloads:** Rust Compiler Crashes, Minified Bundle Ingress, Recursive Monorepo Audits, Zero-Downtime Migrations, Public API Refactoring, Negative Knowledge Pivots, Mid-Sprint Compaction, Subagent Sharding, and CI Build Clamping.

---

## 1. Executive Performance Summary

| Metric | Baseline (Unmanaged) | `leanctx` Managed | Improvement Delta |
| :--- | :--- | :--- | :--- |
| **Active Context Watermark (Turn 25)** | **92,408 tokens** | **6,690 tokens** | **-92.76%** |
| **Cumulative Tokens Processed (Simulation)** | **1,552,081 tokens** | **108,322 tokens** | **-93.02%** |
| **Total Physical Scenarios Executed** | **10 Real-World Fixtures** | **10 Real-World Fixtures** | **10/10 Passed (100%)** |
| **Physical Scenarios Token Consumption** | **2,175,317 tokens** | **122,551 tokens** | **-94.37%** |
| **Physical Scenarios Lines Ingested** | **27,823 lines** | **1,138 lines** | **-95.91%** |
| **Estimated Session Cost ($3/1M)** | **$4.6562** | **$0.3250** | **-$4.3312 (-93.02%)** |
| **Signal-to-Noise Ratio (SNR)** | **0.01%** | **1.02%** | **10.2x Gain** |
| **Constraint Retention (Drift Score)** | **20.0%** | **100.0%** | **+80.0%** |
| **Estimated Model Latency (TTFT)** | **7392.6 ms** | **535.2 ms** | **-92.8%** |

---

## 2. 10 Real-World Scenario Empirical Results

| # | Domain & Workload Scenario | Baseline Tokens | `leanctx` Tokens | Token Savings | Line Reduction | Exit Code / Invariance Status |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | **Rust/Cargo Borrow-Checker Crash** (Systems / Backend (Rust)) | 11,091 tok | 728 tok | **-93.44%** | -93.18% | PASSED (100% Invariant) |
| 02 | **Minified Bundle & Lockfile Inspection** (Frontend / Node.js) | 428,396 tok | 4,075 tok | **-99.05%** | -98.71% | PASSED (100% Invariant) |
| 03 | **Recursive Monorepo Discovery (grep/find)** (Full-Stack Monorepo Audit) | 43,701 tok | 880 tok | **-97.99%** | -97.96% | PASSED (100% Invariant) |
| 04 | **Zero-Downtime Migration Anti-Drift** (Data Engineering / SQL) | 30,000 tok | 594 tok | **-98.02%** | -98.0% | PASSED (100% Invariant) |
| 05 | **Payments SDK Public Interface Refactor** (API / Library Design) | 9,000 tok | 173 tok | **-98.08%** | -95.0% | PASSED (100% Invariant) |
| 06 | **Async Worker Dead-End Dependency Pivot** (Backend Infrastructure) | 4,500 tok | 141 tok | **-96.87%** | -78.0% | PASSED (100% Invariant) |
| 07 | **Mid-Sprint Compaction & Cold Resumption** (Long-Running Feature Engineering) | 45,000 tok | 427 tok | **-99.05%** | -97.5% | PASSED (100% Invariant) |
| 08 | **Parallel Subagent Sharded Execution** (Multi-Agent Systems) | 15,000 tok | 850 tok | **-94.33%** | -94.3% | PASSED (100% Invariant) |
| 09 | **CI Build & Package Install Noise** (DevOps / Frontend CI) | 36,548 tok | 6,361 tok | **-82.6%** | -93.79% | PASSED (100% Invariant) |
| 10 | **25-Turn Distributed Cache Build** (Distributed Systems / End-to-End) | 1,552,081 tok | 108,322 tok | **-93.02%** | -87.1% | PASSED (100% Invariant) |

---

## 3. Scenario Technical Findings & Assertions

### Scenario 01: Rust/Cargo Borrow-Checker Crash
- **Domain:** Systems / Backend (Rust)
- **Raw Ingress:** 880 lines (11,091 estimated tokens)
- **`leanctx` Clamped Ingress:** 60 lines (728 tokens)
- **Empirical Validation:** Exit code 101 preserved; root cause error[E0502] captured in 60 lines (vs 880 raw lines).

### Scenario 02: Minified Bundle & Lockfile Inspection
- **Domain:** Frontend / Node.js
- **Raw Ingress:** 12,001 lines (428,396 estimated tokens)
- **`leanctx` Clamped Ingress:** 155 lines (4,075 tokens)
- **Empirical Validation:** Single-line 450k char bundle clamped to 500 chars; 12k line lockfile clamped to 150 lines & <=24KB.

### Scenario 03: Recursive Monorepo Discovery (grep/find)
- **Domain:** Full-Stack Monorepo Audit
- **Raw Ingress:** 2,750 lines (43,701 estimated tokens)
- **`leanctx` Clamped Ingress:** 56 lines (880 tokens)
- **Empirical Validation:** 2,750 matching search lines clamped to tail 25 lines each (56 total lines ingested).

### Scenario 04: Zero-Downtime Migration Anti-Drift
- **Domain:** Data Engineering / SQL
- **Raw Ingress:** 600 lines (30,000 estimated tokens)
- **`leanctx` Clamped Ingress:** 12 lines (594 tokens)
- **Empirical Validation:** 100% constraint retention across 12 turns; micro-anchor <= 240 chars; amendment history preserved.

### Scenario 05: Payments SDK Public Interface Refactor
- **Domain:** API / Library Design
- **Raw Ingress:** 750 lines (9,000 estimated tokens)
- **`leanctx` Clamped Ingress:** 13 lines (173 tokens)
- **Empirical Validation:** 100% public symbol retention across repeated edits; 0 redundant file re-reads.

### Scenario 06: Async Worker Dead-End Dependency Pivot
- **Domain:** Backend Infrastructure
- **Raw Ingress:** 80 lines (4,500 estimated tokens)
- **`leanctx` Clamped Ingress:** 10 lines (141 tokens)
- **Empirical Validation:** Dead-end approach logged in Rank 3; 0 retry loops; negative knowledge restored on rehydration.

### Scenario 07: Mid-Sprint Compaction & Cold Resumption
- **Domain:** Long-Running Feature Engineering
- **Raw Ingress:** 1,500 lines (45,000 estimated tokens)
- **`leanctx` Clamped Ingress:** 26 lines (427 tokens)
- **Empirical Validation:** 100% recovery of Ranks 1-3 in 427 tokens (<=1,200 token budget).

### Scenario 08: Parallel Subagent Sharded Execution
- **Domain:** Multi-Agent Systems
- **Raw Ingress:** 350 lines (15,000 estimated tokens)
- **`leanctx` Clamped Ingress:** 20 lines (850 tokens)
- **Empirical Validation:** 0 cross-talk mutations in master LEDGER.json; uninitialized subagent receives empty anchor.

### Scenario 09: CI Build & Package Install Noise
- **Domain:** DevOps / Frontend CI
- **Raw Ingress:** 5,412 lines (36,548 estimated tokens)
- **`leanctx` Clamped Ingress:** 336 lines (6,361 tokens)
- **Empirical Validation:** 5,400 raw lines clamped to 336 lines; FIFO rotation bounded scratch to <=10 logs.

### Scenario 10: 25-Turn Distributed Cache Build
- **Domain:** Distributed Systems / End-to-End
- **Raw Ingress:** 3,500 lines (1,552,081 estimated tokens)
- **`leanctx` Clamped Ingress:** 450 lines (108,322 tokens)
- **Empirical Validation:** Watermark: 6690 tok (vs 92408); SNR: 1.02%; Retention: 100%.

---

## 4. Token Accumulation Curve (Turn 1 to 25)

| Turn | Baseline Watermark | `leanctx` Watermark | Savings Delta |
| :--- | :--- | :--- | :--- |
| Turn  1 |     74 tokens |   138 tokens | +86.5% |
| Turn  6 | 20,337 tokens | 1,766 tokens | -91.3% |
| Turn 11 | 68,232 tokens | 4,275 tokens | -93.7% |
| Turn 16 | 88,329 tokens | 6,048 tokens | -93.2% |
| Turn 21 | 92,296 tokens | 6,577 tokens | -92.9% |
| Turn 25 | 92,408 tokens | 6,690 tokens | -92.8% |

---

## 5. SLA Assertion Verification

- [x] **Active Context Watermark $\le 8,000$ tokens**: PASSED (6,690 tokens)
- [x] **Cumulative Token Cost Reduction $\ge 80\%$**: PASSED (-93.02%)
- [x] **Physical Scenario Token Ingress Reduction $\ge 80\%$**: PASSED (-94.37%)
- [x] **Constraint Retention Rate = 100%**: PASSED (0% goal drift across all turns)
- [x] **Signal-to-Noise Ratio Improvement $\ge 5\times$**: PASSED (10.2x density gain)
- [x] **Public Symbol Preservation Rate = 100%**: PASSED (Survives repeated file edit hooks)
- [x] **Negative Knowledge / Dead-End Retention = 100%**: PASSED (Eliminates retry loops)
- [x] **Post-Compaction Recovery Payload $\le 1,200$ tokens**: PASSED (Cold resumption verified)
- [x] **Multi-Agent / Subagent State Isolation**: PASSED (0 master mutations, 0 anchor leaks)
