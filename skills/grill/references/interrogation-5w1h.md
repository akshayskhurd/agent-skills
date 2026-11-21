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
- **Who isolates subagent state?** In multi-agent or subagent execution, what prevents ephemeral workers from corrupting coordinator state?

### 📦 WHAT
- **What are the preconditions and invariants?** What exact schema, format, and ranges are required for inputs?
- **What are the platform limits?** Does the underlying platform, runtime, or API physically support the requested operation?
- **What exact serialization schema is required?** Does the runtime require nested protojson objects or flat dictionaries?
- **What happens on unexpected input?** Does it raise a typed error, return null, or corrupt memory?
- **What are the side effects?** Does this write to disk, mutate a database, emit events, or alter arguments passed by reference?
- **What guarantees does this provide?** Is the operation atomic? Idempotent? Strongly consistent? Eventually consistent?
- **What is the failure policy?** Does it fail-open or fail-closed? Can a failure in an auxiliary component abort the main execution loop?

### ⏱️ WHEN
- **When is this executed?** Is it in the critical request-response path, or is it an asynchronous background job?
- **When does it timeout?** What is the exact deadline? What happens when network latency spikes?
- **When does execution block?** What happens if a command is a long-running daemon (`IsDaemon: true`) or interactive process?
- **When can races occur?** Can two concurrent threads or processes execute this simultaneously? What locks or transactional isolations protect it?
- **When does state expire?** When is memory freed, connections closed, and caches invalidated?

### 📍 WHERE
- **Where does execution take place?** In the client browser, edge proxy, application server, or database engine?
- **Where are shell commands executed?** Does execution run in POSIX `/bin/sh`, Bash, or Zsh? Are all paths and metacharacters quoted?
- **Where are errors routed?** Do they appear in stderr, an observability pipeline, or are they swallowed?
- **Where are secrets stored?** In environment variables, vault services, or committed to memory?
- **Where are scratch files placed?** Are temporary files stored with restricted permissions (`0700`), capped storage quotas, and ignored by `.gitignore`?
- **Where are network boundaries crossed?** Does this call cross availability zones, VPCs, or third-party internet boundaries?

### 💡 WHY
- **Why was this approach chosen?** Is this complexity justified by concrete requirements, or is it speculative over-engineering?
- **Why is this dependency necessary?** Could standard library primitives solve this without introducing supply-chain risks?
- **Why does this default exist?** Is the default configuration secure and optimal, or dangerous?
- **Why assume platform capabilities?** What documentation or empirical proof verifies the host runtime actually provides this hook or feature?

### ⚙️ HOW
- **How does it recover from catastrophic failure?** Can it resume cleanly after a power loss, network partition, or crash?
- **How are root-cause errors preserved?** Does output truncation preserve both initial compiler panics and final exit summaries (Head/Tail sandwich)?
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
| *"Platform supports modifying memory/history."* | *"Does the host API actually provide a deletion/pruning hook, or is history held in-memory by the runtime?"* | Verify physical API capability against official runtime documentation. Speculation is **PROHIBITED**. |
| *"Tool output is parsed from hook stdin."* | *"Does the hook protocol actually pipe stdout to stdin, or does it pass only invocation metadata?"* | Verify exact stdin JSON schema from official platform contracts. |
| *"Commands can be wrapped with redirection."* | *"What happens if the command is a daemon, background watcher, or interactive process?"* | Explicit daemon bypass (`IsDaemon: true`) and shell quoting **MUST** be present. |
| *"Subagents execute tool calls independently."* | *"What prevents subagent hook executions from corrupting coordinator shared state?"* | Enforce master session identification and state isolation. |

---

## 3. Reasoning Before Concluding

The agent **MUST NEVER** emit a verdict or apply a fix without documenting the causal chain:

1. **Observed Syntax / Architecture**: Exact snippet and context.
2. **Defect Mechanism**: The specific sequence of events that triggers failure.
3. **Worst-Case Consequence**: Security breach, data loss, deadlock, memory leak, or crash.
4. **Counter-Evidence Evaluation**: Any existing mitigations and why they are insufficient.
5. **Imperative Directive**: The single unambiguous fix that **MUST** be executed.
