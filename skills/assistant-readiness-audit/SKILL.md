---
name: assistant-readiness-audit
description: Audit whether an AI assistant is truly operational across identity, channels, routing, schedulers, permissions and end-to-end readback. Use for readiness reviews and setup diagnosis, not to provision accounts or send test messages without approval.
---

# Assistant Readiness Audit

Distinguish configured components from a working end-to-end assistant.

## Build the inventory

Record the assistant's intended identity, host, gateway, agent, channel accounts, bindings, scheduler, knowledge sources, permission tiers and user-visible destinations. Redact addresses, tokens, phone numbers and private content from the report.

Check for singleton components before starting anything. Duplicate gateways, schedulers or channel listeners can cause double delivery and inconsistent state.

## Verify layer by layer

1. **Identity:** the intended OS, service and channel accounts are authenticated as the expected identity.
2. **Runtime:** exactly the intended gateway and agent processes are healthy on the intended host.
3. **Channel:** the plugin exists, the account is configured, routing is bound and the destination is reachable.
4. **Scheduler:** jobs have one owner and one active scheduler; skipped or duplicate jobs are explained.
5. **Knowledge:** sources are current and permission boundaries are enforced by connectors or services, not instructions alone.
6. **Network:** local, tunnel and remote paths are verified independently. A local permission error is not automatically a remote outage.
7. **User experience:** the actual recipient can send, receive and continue a bounded test interaction.

Read-only inspection does not authorise creating identities, enabling channels, sending messages, changing DNS, granting permissions or starting paid services.

## Completion standard

For each layer report `verified`, `configured_not_verified`, `blocked` or `not_configured`, plus evidence timestamp and next action. Configuration, registration and health endpoints are not end-to-end proof.

Never mark the assistant operational until a user-visible round trip has been observed through the intended identity, route and destination. If a safe test would message another person or expose private context, request exact approval first.
