# Exemplar: End-to-End Telescope Workflow

## Scenario: Building a Resilient Rate-Limited Webhook Dispatcher

### 1. Macro Zoom-Out (Initial Formulation)
- **High-Level Requirement**: Dispatch signed webhooks to external endpoints with exponential backoff and rate limiting.
- **Living Perspective State**:
  - Task 1: Payload signer and HMAC SHA-256 serializer.
  - Task 2: Token-bucket rate limiter.
  - Task 3: HTTP dispatcher with exponential backoff retry.

---

### 2. Micro Zoom-In (Task 1 Execution)
- **Executor**: Single-Pass Executor generates HMAC payload signer.
- **Micro Grill**: Developer & Security personas verify constant-time comparison (`hmac.compare_digest`) and secret masking.
- **Outcome**: Task 1 passes zero defects.

---

### 3. Macro Zoom-Out (Perspective Check & Clarification Gate)
- **Sanity Check**: Reviewing Task 1 output reveals an unaddressed requirement: What happens when the external endpoint returns HTTP 429 vs 500?
- **Clarification Action**:
  - Agent halts before building Task 3.
  - Formulates question: *"Should HTTP 429 backoff adhere strictly to the `Retry-After` header or use client exponential backoff?"*
  - User confirms: *"Adhere to `Retry-After` if present, otherwise default to exponential backoff."*
- **State Update**: Record decision in `PERSPECTIVE.md` and refine Task 3 contract.

---

### 4. Micro Zoom-In (Tasks 2 & 3 Execution)
- Execute Task 2 (Token Bucket) and Task 3 (Dispatcher with `Retry-After` handling).
- Micro Grill passes each task to zero defects.

---

### 5. Final Macro Zoom-Out (System Grill)
- Macro Grill runs Architect, SRE, and DX personas across the aggregated codebase.
- Verified: End-to-end integration passes zero defects.
