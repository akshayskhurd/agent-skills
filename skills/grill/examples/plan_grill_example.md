# Plan / Architecture Grill Walkthrough

This example demonstrates how the **Grill** protocol scrutinizes an engineering plan or architecture design document.

---

## 1. Original Vague / Optimistic Plan

> **Original Plan Proposal:**
> "We will add a webhook listener to receive payment updates from Stripe. The endpoint will verify the payload and then update the user account database directly to grant pro access. If the database update fails, it will send an alert to Slack. This will easily support our expected 1,000 requests per second."

---

## 2. Stage 1 & 2: 9-Persona & 5W1H Interrogation

### Sentence 1: *"We will add a webhook listener to receive payment updates from Stripe."*
- **SRE & Reliability**: What happens if Stripe experiences network jitter and retries duplicate webhooks?
- **5W1H Counter-Question**: *How is idempotency enforced?*
- **Imperative Directive**: **MUST** record each webhook `event.id` in a dedicated idempotency table with unique constraints before processing.

### Sentence 2: *"The endpoint will verify the payload and then update the user account database directly to grant pro access."*
- **Security Researcher**: How is the payload verified? Does it verify HMAC signatures against the raw body or parsed JSON?
- **Architect & Cost Optimizer**: Direct synchronous database mutation during the webhook HTTP handler causes thread pool exhaustion when database latency spikes under load.
- **5W1H Counter-Question**: *Who verifies that the secret hasn't been rotated? Where does the raw request stream live?*
- **Imperative Directive**:
  1. The handler **MUST** verify Stripe HMAC signatures using the raw unparsed request body.
  2. The handler **MUST NOT** synchronously mutate user accounts; it **MUST** enqueue a job into a durable message queue (e.g., SQS/Redis/Kafka) and acknowledge with HTTP 200 within 500ms.

### Sentence 3: *"If the database update fails, it will send an alert to Slack."*
- **Tester & SRE**: What if Slack API is rate-limited or unavailable during a database outage? The failure is permanently lost.
- **Imperative Directive**: Failures **MUST** trigger message dead-lettering (DLQ) with exponential retry backoff. Slack alerts **MUST** be an auxiliary metric subscriber, not the primary failure handling mechanism.

### Sentence 4: *"This will easily support our expected 1,000 requests per second."*
- **Performance & Cost Optimizer**: 1,000 RPS direct synchronous database writes will exhaust connection pools and incur massive IOPS costs.
- **5W1H Counter-Question**: *What benchmark proves 1,000 RPS against the production DB?*
- **Imperative Directive**: **MUST** batch message consumer writes and maintain read replicas or connection poolers (e.g., PgBouncer).

---

## 3. Remediated & Certified Architectural Plan

> **Certified Robust Plan:**
> 1. **Ingestion & Signature Verification**:
>    - The HTTP endpoint **MUST** capture raw payload bytes and verify the `Stripe-Signature` header using `stripe.Webhook.construct_event` and the active endpoint secret.
>    - The endpoint **MUST** reject unverified requests with HTTP 400 immediately.
> 2. **Durable Decoupled Ingestion**:
>    - Verified events **MUST** be pushed to a FIFO message queue (with message deduplication ID set to `event.id`).
>    - The endpoint **MUST** respond with HTTP 200 within 500ms of queue acknowledgment.
> 3. **Idempotent Asynchronous Processing**:
>    - Worker consumers **MUST** start a database transaction, check `processed_events` table for `event.id`, and ignore if already processed.
>    - Account status **MUST** transition from `pending` to `pro` in the same transaction.
> 4. **Resilience & Dead Letter Queue (DLQ)**:
>    - Failed worker jobs **MUST** retry up to 5 times with exponential backoff and jitter.
>    - After 5 failures, messages **MUST** route to a Dead Letter Queue with an automated pager alert for manual inspection.
