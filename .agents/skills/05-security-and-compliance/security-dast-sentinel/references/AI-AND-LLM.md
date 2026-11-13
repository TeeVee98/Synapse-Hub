<!--
SPDX-FileCopyrightText: Copyright (c) Cloudflare, Inc.
SPDX-License-Identifier: MIT
Adapted from cloudflare/security-audit-skill for Synapse-Hub Enterprise QA.
-->

# AI, LLM, and Autonomous Agent Security Hunting

#### When to use this guide

Reach for this guide whenever a language model or AI agent participates in a trust-sensitive decision: chatbots, RAG pipelines, persistent agent memory, autonomous tool-calling loops, MCP servers and clients, code that builds prompts from untrusted input, or code that consumes model output and executes actions. The critical data flow is:
`untrusted content → model / agent memory → capability, authority, or sink`.

Use this alongside `ATTACK-CLASSES.md`, not instead of it. Transport, access control, query construction, filesystem use, and output rendering remain ordinary trust boundaries. This guide covers the model-specific delegation layer.

---

## 1. Core Defensive Discipline

```text
1. Prompt injection alone is not a defect. Require a code-level boundary failure: content reaches another principal's context, invokes authority the requester lacks, discloses data they cannot read, or drives a sink they cannot reach directly.
2. Model output, memory, tool descriptions, and MCP responses are untrusted inputs. Point to the code that grants authority, trusts output, writes durable state, or feeds a sink.
3. A guardrail prompt is not a security boundary. Count only deterministic checks, resource-scoped authorization, isolation, binding, and constrained credentials.
4. State the attacker, affected principal, effective execution identity, resource, exact action, authority used, and observable impact. An intentional direct request to use the requester's existing authority is not a delegation defect merely because a model executes it.
5. Authorization and action binding are separate controls. Attacker-controlled content causing an action under an affected principal's valid authority is an action-binding failure when that principal did not intentionally request or approve the exact action.
6. Classify every candidate as confirmed only after source evidence and bounded local validation establish the boundary and result. Use needs_validation when a required provider, deployment, model, renderer, or identity behavior is not observable locally.
```

---

## 2. Context, Retrieval, and Memory Attack Classes

### Indirect Injection Through Ingested Content
An attacker writes an untrusted document, issue title, git commit, customer review, or tool response that enters an agent's model context.
- **Trace:** Who can write each input source? Whose session consumes it? What capability is enabled in that session?
- **Defect:** Missing deterministic sanitization before feeding downstream sinks or tool handlers.

### Cross-Session or Cross-Tenant Context Bleed
Conversation history, vector embeddings, RAG results, or prompt cache entries are keyed too broadly across tenants.
- **Verification:** Ensure tenant and ACL filters are included in the query itself and in every cache key. A tenant field stored on an object is NOT enforcement if an alternate query or shared cache omits it.

### Persistent Memory Poisoning
Attacker-controlled content or model hallucinations are saved into long-term memory (`qa-memory-os`, vector DB, or user profile) that later shapes another task, user, or privileged session.
- **Verification:** Check who may create, update, or merge memory records. Low-trust observations must never become durable system instructions or tool policies.

### Prompt Role and Provenance Confusion
Prompt assembly lets untrusted text impersonate a system message, prior turn, tool result, policy, or memory record. Look for string concatenation, untyped history, caller-controlled role fields, and serialization round trips that lose source labels. Confirm that the forged provenance changes a deterministic trust decision or reaches a meaningful capability.

---

## 3. Tool and Action Attack Classes

### Tool-Argument Injection into a Downstream Sink
Model-produced arguments reach SQL queries, shell commands (`powershell`, `bash`), file paths, or external privileged APIs without handler-side validation.
- **Verification:** Structured output/JSON schema narrows input shape; it does NOT establish authorization, path traversal safety, URL allowlists, or safe query semantics. Every tool handler must re-validate arguments before execution.

### Excessive Agency & Confused Deputy Authority
The AI agent operates using a broad service account or elevated identity, while the tool handler fails to re-check the requesting user's explicit permissions on the target resource.
- **Verification:** Both the effective identity and the requesting principal's permissions must be verified for the exact resource requested.

### Action-Confirmation and Approval Binding
A user approves action A, but the agent's execution loop executes action B (mutated arguments, different resource ID, or duplicated side effect). An action-binding defect also exists when attacker-controlled content causes a side effect under a victim's valid authority without intentional approval.
- **Verification:** An approval token must bind the normalized tool name, exact argument payload hash, requester ID, target resource, and single-use expiration. Resumed sessions or retries must never re-use a prior approval for a mutated side effect.

### Tool-Schema and Dispatcher Disagreement
The schema accepts aliases, extra fields, duplicate keys, coercions, nested free-form objects, or out-of-range values that the dispatcher or handler interprets differently. Compare schema validation, canonicalization, generated bindings, and handler defaults. Validate again where values become resource selectors or security-relevant options.

### Unbounded Delegated Action Loops
A bounded request can enqueue repeated spend, send, mutation, or external API work without a per-request budget, per-action authorization, cancellation, or idempotency control. Confirm impact on shared cost, quotas, other users, or durable state. Do not test by exhausting a service; use code-level accounting and a locally bounded loop.

---

## 4. MCP and Multi-Agent Swarm Trust Classes

### Sub-Agent and MCP Trust Inheritance
A delegated subagent receives full session credentials, environment secrets, or unrestricted tool access rather than the least authority required.
- **Verification:** Capability narrowing must apply at each delegation hop. Subagent results must be validated as untrusted inputs upon return.

### MCP Server & Tool Identity Confusion
Tool dispatch routes calls by model-influenced names rather than verified server connection handles. Two MCP servers must not be allowed to hijack or override the same tool namespace. Check whether reconnect changes the binding, and whether a response from one server can satisfy another server's pending call.

### MCP Metadata and Schema as Policy
Tool descriptions, resource metadata, prompts, completion hints, or schemas supplied by an MCP peer are trusted as policy or authorization. These fields can guide the model but cannot grant capability. Find the deterministic allowlist, server identity check, and handler authorization that remain authoritative when metadata conflicts.

---

## 5. Output and Disclosure Attack Classes

### Insecure Output Rendering
Model output reaches an executing HTML, Markdown, template, URL, or command sink without the sink's required encoding and policy. For browser rendering, verify auto-loaded resources and CSP or sanitization; renderer behavior outside the repository makes the candidate `needs_validation`.

### Sensitive Context Extraction
Model contexts containing system API keys, database credentials, or other tenants' data are tricked into emitting secrets in output text, markdown files, or log artifacts.
- **Verification:** Redact secrets before prompt assembly and filter model outputs with regex scrubbing before writing to disk.

---

## 6. Universal Moves (Hunting Methodology)

- Draw four maps first: each execution identity, each capability, every writable context or memory source, and each output destination. Then connect the principal at the start to the authority at the end.
- Start at side-effecting tools and work backward through dispatcher, schema, confirmation, model context, retrieval, and ingestion. Start at durable memory reads and trace every writer.
- Compare direct, queued, retry, resume, batch, and delegated paths for the same action. The strongest gate must apply after arguments are final and before every side effect.

---

## 7. Validation Rules (Apply Before Reporting Any Finding)

1. **Name the crossed boundary and observable result**: attacker, affected principal or shared resource, execution identity, target, and unauthorized or unrequested action or disclosure.
2. **Prove authority or binding failure**: For confused-deputy claims, prove the tool lacks requester-and-resource authorization and that the attacker cannot perform the same action normally. For action-binding claims, prove attacker-controlled content caused an action under the affected principal's authority without intentional request or approval.
3. **Trace writes and reads for memory claims**: For memory or retrieval claims, cite both the attacker-controlled write and the later cross-principal read or privileged decision.
4. **Compare approved intent with executed object**: Establish the intentional request or normalized approved object, if any, and compare it with the object the handler uses. Confirm locally observable unrequested action or mutation.
5. **Verify MCP connections**: Verify authenticated connection, request correlation, tool namespace, and effective credential. Mark `needs_validation` if external server routing is required.
6. **Classify strictly**: Return `confirmed` findings only with complete source trace and meaningful result. Return `needs_validation` for specific unresolved boundary facts and state the bounded local check needed to resolve them.
