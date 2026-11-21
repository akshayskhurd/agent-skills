# Empirical Benchmark Report: `leanctx` vs Baseline

**Evaluation Scope:** Head-to-Head Multi-Turn Simulation (25 Turns)  
**Workload Profile:** Realistic Codebase Refactoring (Large File Reads, Webpack Builds, Failing Tests & Stack Traces, Constraint Verification)

---

## 1. Executive Performance Summary

| Metric | Baseline (Unmanaged) | `leanctx` Managed | Improvement Delta |
| :--- | :--- | :--- | :--- |
| **Active Context Watermark (Turn 25)** | **92,408 tokens** | **6,660 tokens** | **-92.79%** |
| **Cumulative Tokens Processed** | **1,552,081 tokens** | **107,582 tokens** | **-93.07%** |
| **Estimated Session Cost ($3/1M)** | **$4.6562** | **$0.3227** | **-$4.3335 (-93.07%)** |
| **Signal-to-Noise Ratio (SNR)** | **0.01%** | **0.57%** | **5.7x Gain** |
| **Constraint Retention (Drift Score)** | **20.0%** | **100.0%** | **+80.0%** |
| **Estimated Model Latency (TTFT)** | **7392.6 ms** | **532.8 ms** | **-92.8%** |

---

## 2. Token Accumulation Curve (Turn 1 to 25)

| Turn | Baseline Watermark | `leanctx` Watermark | Savings Delta |
| :--- | :--- | :--- | :--- |
| Turn  1 |     74 tokens |   108 tokens | +45.9% |
| Turn  6 | 20,337 tokens | 1,737 tokens | -91.5% |
| Turn 11 | 68,232 tokens | 4,245 tokens | -93.8% |
| Turn 16 | 88,329 tokens | 6,018 tokens | -93.2% |
| Turn 21 | 92,296 tokens | 6,548 tokens | -92.9% |
| Turn 25 | 92,408 tokens | 6,660 tokens | -92.8% |

---

## 3. Physical Subprocess & Disk Benchmark (Live Execution)

| Metric | Raw Subprocess Execution | `leanctx` Sandboxed Execution | Physical Delta |
| :--- | :--- | :--- | :--- |
| **Ingested Lines (Command + File Read)** | **1403 lines** | **210 lines** | **-85.0% lines** |
| **Physical Output Tokens Generated** | **9,263 tokens** | **1,605 tokens** | **-82.67% tokens** |

---

## 4. SLA Assertion Verification

- [x] **Active Context Watermark $\le 8,000$ tokens**: PASSED (6,660 tokens)
- [x] **Cumulative Token Cost Reduction $\ge 80\%$**: PASSED (-93.07%)
- [x] **Constraint Retention Rate = 100%**: PASSED (0% goal drift across all turns)
- [x] **Signal-to-Noise Ratio Improvement**: PASSED (5.7x density gain)
