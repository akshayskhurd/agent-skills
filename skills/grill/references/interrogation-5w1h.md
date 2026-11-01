# The 5W1H Interrogation & Counter-Claiming Protocol

The Grill skill requires rigorous, adversarial Socratic interrogation. The agent **MUST NOT** accept assumptions, claims, or code structure at face value. Every assertion must be aggressively pressure-tested before reaching any conclusion.

---

## 1. The 5W1H Diagnostic Matrix

Every component, function, architecture block, or documentation section **MUST** answer the following questions:

### 👤 WHO
- **Who calls this?** Who is the intended consumer (internal service, anonymous user, administrator, scheduled job)?
- **Who owns the state?** Which component is the single source of truth for the data being manipulated?
- **Who has authorization?** Does the caller have verified credentials and sufficient privileges to execute this operation?
- **Who is impacted on failure?** If this fails, does it degrade a single user session or crash the entire cluster?

### 📦 WHAT
- **What are the preconditions and invariants?** What exact schema, format, and ranges are required for inputs?
- **What happens on unexpected input?** Does it raise a typed error, return null, or corrupt memory?
- **What are the side effects?** Does this write to disk, mutate a database, emit events, or alter arguments passed by reference?
- **What guarantees does this provide?** Is the operation atomic? Idempotent? Strongly consistent? Eventually consistent?

### ⏱️ WHEN
- **When is this executed?** Is it in the critical request-response path, or is it an asynchronous background job?
- **When does it timeout?** What is the exact deadline? What happens when network latency spikes?
- **When can races occur?** Can two concurrent threads or processes execute this simultaneously? What locks or transactional isolations protect it?
- **When does state expire?** When is memory freed, connections closed, and caches invalidated?

### 📍 WHERE
- **Where does execution take place?** In the client browser, edge proxy, application server, or database engine?
- **Where are errors routed?** Do they appear in stderr, an observability pipeline, or are they swallowed?
- **Where are secrets stored?** In environment variables, vault services, or committed to memory?
- **Where are network boundaries crossed?** Does this call cross availability zones, VPCs, or third-party internet boundaries?

### 💡 WHY
- **Why was this approach chosen?** Is this complexity justified by concrete requirements, or is it speculative over-engineering?
- **Why is this dependency necessary?** Could standard library primitives solve this without introducing supply-chain risks?
- **Why does this default exist?** Is the default configuration secure and optimal, or dangerous?

### ⚙️ HOW
- **How does it recover from catastrophic failure?** Can it resume cleanly after a power loss, network partition, or crash?
- **How does it scale under load?** What is the asymptotic bottleneck ($O(N)$, database connection pool exhaustion, file descriptor limits)?
- **How is it tested and observed?** Is there unit test coverage, integration tests, and structured telemetry?
- **How can an adversary exploit it?** How could a malicious actor manipulate timing, inputs, or concurrency to break invariants?

---

## 2. Adversarial Counter-Questioning Framework

Whenever code or documentation asserts a claim, the agent **MUST** execute the 3-step Counter-Questioning sequence:

```
[Claim Asserted] ──> [Invert & Attack] ──> [Demand Proof / Trace Code] ──> [Imperative Verdict]
```

### Standard Claim vs. Counter-Question Patterns

| Claim in Code / Plan | The Hostile Counter-Question | Verification Requirement |
|---|---|---|
| *"Input is pre-validated by caller."* | *"What if an internal service is bypassed, or an unauthenticated route reaches this method?"* | Code **MUST** enforce defensive validation at the method boundary. |
| *"This operation is thread-safe."* | *"What happens if Thread A reads while Thread B is mid-write, or during teardown?"* | Verify mutex locks, atomic variables, or immutability. |
| *"Database queries are fast because of indexes."* | *"What happens when the table grows to 10M rows and the query triggers a full table scan due to a type mismatch?"* | Verify index coverage and query plan behavior. |
| *"This API call will always return within 200ms."* | *"What happens during upstream outage, DNS failure, or packet loss?"* | Explicit connection and read timeouts **MUST** be present. |
| *"Token is verified downstream."* | *"What prevents confused-deputy attacks or forged claims between services?"* | Verify cryptographic verification and audience/issuer validation. |
| *"This will never be null."* | *"What if deserialization fails, or the schema evolves upstream?"* | Strict nullability checks and guard clauses **MUST** be implemented. |

---

## 3. Reasoning Before Concluding

The agent **MUST NEVER** emit a verdict or apply a fix without documenting the causal chain:

1. **Observed Syntax / Architecture**: Exact snippet and context.
2. **Defect Mechanism**: The specific sequence of events that triggers failure.
3. **Worst-Case Consequence**: Security breach, data loss, deadlock, memory leak, or crash.
4. **Counter-Evidence Evaluation**: Any existing mitigations and why they are insufficient.
5. **Imperative Directive**: The single unambiguous fix that **MUST** be executed.
