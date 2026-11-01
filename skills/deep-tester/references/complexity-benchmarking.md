# Cross-Language Asymptotic Complexity Verification & Benchmarking Standards

## 1. Asymptotic Ratio Verification Protocol

To verify whether an algorithm conforms to $O(N)$ vs $O(N^2)$ without false positives from CPU jitter, test runners MUST:
1. Warm up CPU caches and trigger garbage collection prior to timing.
2. Execute a minimum of 5 iterations and record the **median execution time**.
3. Compute the scaling ratio: $R = \text{Median}(T(10N)) / \max(\text{Median}(T(N)), 10^{-9})$.
4. For expected $O(N)$, assert $R < 20.0$ (allowing for memory bus and cache-miss overhead). For $O(N^2)$, $R \ge 80.0$.

---

## 2. Cross-Language Native Benchmarking Harnesses

| Language | Test Framework | Benchmark Primitive | Allocation Profiler |
| :--- | :--- | :--- | :--- |
| **Python** | `pytest` | `pytest-benchmark` / `time.perf_counter()` | `tracemalloc` / `cProfile` |
| **TypeScript / JS** | `vitest` / `jest` | `vitest bench` / `tinybench` / `performance.now()` | `process.memoryUsage()` / Chrome DevTools V8 profiler |
| **Go** | `testing` | `func BenchmarkX(b *testing.B)` | `b.ReportAllocs()` / `pprof` |
| **Rust** | `cargo` | `cargo bench` / `criterion` | `dhat` / `heaptrack` |
| **Java** | `JUnit 5` | `JMH (Java Microbenchmark Harness)` | `Async-profiler` / JFR |

---

## 3. Complexity Reduction Prescriptions

When asymptotic tests indicate super-linear scaling on expected $O(N)$ operations:
1. **Unindexed Lookups**: Convert list or slice traversal to hash sets (`Set` in TS, `map[K]struct{}` in Go, `HashSet` in Rust/Java) for $O(1)$ lookups.
2. **String Allocations**: In loops, replace string concatenation with pre-allocated builders (`strings.Builder` in Go, `StringBuilder` in Java, `Vec<u8>` in Rust).
3. **Repeated Compilations**: Hoist regex compilations and schema parsers to module or package initialization.
4. **Sorting Overhead**: Maintain a heap or priority queue instead of sorting entire collections repeatedly.

---

## 4. Benchmark Isolation

- Benchmark tests MUST be decorated or tagged with native markers (`@pytest.mark.benchmark`, `b.ResetTimer()`, `criterion::black_box`).
- Fast unit suites MUST execute independently of benchmark suites to guarantee sub-second developer feedback.
