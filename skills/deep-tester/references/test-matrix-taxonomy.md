# Cross-Language Multi-Vector Test Engineering Taxonomy

Comprehensive testing requirements applicable across Python, TypeScript/JavaScript, Go, Rust, and Java.

---

## 1. Vector A: Functional Coverage Invariants

### Numeric Boundaries
- MUST assert exact handling for: $0$, $-0$, $1$, $-1$, $\text{MAX\_INT}$, $\text{MIN\_INT}$, $\infty$, $-\infty$, and $\text{NaN}$.
- Floating point assertions MUST exclusively use approximate equality helpers:
  * **Python**: `pytest.approx(expected, rel=1e-6)` or `math.isclose()`
  * **TypeScript/JS**: `expect(actual).toBeCloseTo(expected, 5)` or `Math.abs(a - b) < Number.EPSILON`
  * **Go**: `math.Abs(a - b) <= epsilon`
  * **Rust**: `approx::assert_relative_eq!(a, b, epsilon = 1e-6)`
  * **Java**: `assertEquals(expected, actual, 1e-6)`

### String & Binary Boundaries
- MUST verify:
  1. Empty string (`""`) and whitespace-only (`"   "`).
  2. Embedded null bytes (`"foo\x00bar"`).
  3. Multi-byte Unicode graphemes (e.g., family emoji `"👨‍👩‍👧‍👦"`).
  4. Bidirectional text overrides (`"\u202e"`).
  5. Maximum buffer lengths ($N=65536$).

---

## 2. Vector B: Security & Adversarial Vectors

### Injection & Boundary Resistance
- **Path Traversal**: Payloads MUST include `"../../etc/passwd"` and `"..\\..\\windows\\system32"`. Tests MUST execute against in-memory mock filesystems or ephemeral temporary directories. Direct interaction with host filesystem roots is PROHIBITED.
- **SQL / Command Injection**: Payloads MUST include `"' OR '1'='1"`, `"; rm -rf /"`, and `"` | id`. Parameterized query execution MUST be asserted.
- **ReDoS Protection**: Any regex performance test MUST execute within a subprocess or watchdog thread with a hard timeout of $500\text{ms}$. Indefinite regex execution in the test runner is FORBIDDEN.

### Cryptographic & Auth Invariants
- Token comparisons MUST assert constant-time equality:
  * **Python**: `hmac.compare_digest(a, b)`
  * **TypeScript/JS**: `crypto.timingSafeEqual(bufA, bufB)`
  * **Go**: `subtle.ConstantTimeCompare(a, b)`
  * **Rust**: `subtle::ConstantTimeEq`
  * **Java**: `MessageDigest.isEqual(a, b)`
- Auth tests MUST verify tenant boundary isolation: user with Tenant A credentials MUST receive `403 Forbidden` on Tenant B resources.

---

## 3. Vector C: Resource & Leak Profiling

### Memory Growth Checks
- **Python**: Use `tracemalloc.take_snapshot()` before and after 1,000 iterations.
- **TypeScript/Node**: Inspect `process.memoryUsage().heapUsed` before and after loop with `global.gc()`.
- **Go**: Inspect `runtime.ReadMemStats(&m)` and assert `m.Alloc` delta $< \text{threshold}$.
- **Rust**: Use custom allocator tracking (`stats_alloc`) or valgrind/miri checks.
- **Java**: Inspect `Runtime.getRuntime().totalMemory() - freeMemory()`.

### CPU Circuit Breakers
- Heavy recursive or looping functions MUST include recursion limit checks or step counters.
- Tests MUST assert that reaching maximum depth raises a typed domain exception, NEVER a runtime crash.

---

## 4. Vector D: External Dependency Isolation

### Ephemeral Port Binding
- When testing HTTP client behavior with mock servers, tests MUST bind to ephemeral port `0`:
  * **Python**: `sock.bind(("127.0.0.1", 0))`
  * **TypeScript/Node**: `server.listen(0)`
  * **Go**: `net.Listen("tcp", "127.0.0.1:0")`
  * **Rust**: `TcpListener::bind("127.0.0.1:0")`
  * **Java**: `new ServerSocket(0)`
- Hardcoded test ports (e.g. `8080`, `3000`) are STRICTLY FORBIDDEN.

### Failure Injections
- Test suites MUST simulate:
  1. Connection refused (`ECONNREFUSED`).
  2. Read timeouts (`ETIMEDOUT`).
  3. HTTP `429 Too Many Requests` with `Retry-After`.
  4. HTTP `503 Service Unavailable` with transient recovery.
