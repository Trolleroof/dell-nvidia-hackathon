# OpenShell Sandboxing Rules

The security model must rely on enforced architectural boundaries rather than trusting the LLM to obey prompt instructions.

## Core Principles

### 1. Out-of-Process Policy Enforcement

Security policies must be enforced outside of the agent runtime.

The policy engine acts as a gatekeeper between:

- the Claw orchestrators,
- the MCP,
- the host infrastructure.

All actions requested by the agent must pass through this policy layer before execution.

Benefits:

- Prevents prompt injection from bypassing security controls.
- Prevents hallucinated permissions from being honored.
- Ensures security decisions are independent of model outputs.
- Provides auditable and deterministic enforcement.

### 2. Filesystem and Process Containment

The agent must execute within a sandboxed environment.

Requirements:

- Restrict filesystem access to explicitly allowed directories.
- Prevent access to host operating system resources.
- Drop unnecessary capabilities and privileges.
- Enforce process limits and resource quotas.
- Prevent execution of arbitrary host binaries.
- Prevent execution of arbitrary shell scripts unless explicitly approved by policy.

The agent should only interact with resources exposed through approved interfaces.

### 3. Network Egress Control

The default network policy is deny-by-default.

Requirements:

- Block outbound network access unless explicitly permitted.
- Allow network access only through predefined policies or presets.
- Log all approved outbound requests.
- Restrict communication to approved endpoints and protocols.

Examples:

- Telegram Bot integration.
- Brave Search API.
- Internal APIs explicitly approved by the deployment configuration.

### 4. Routed Inference

NemoClaw is responsible for inference routing.

The system must support configurable inference backends, including:

- Local models.
- Private hosted models.
- External cloud providers.

For privacy-sensitive deployments:

- Route inference to local models (e.g., Ollama).
- Prevent sensitive data from leaving the local environment.
- Ensure prompts, simulation states, and reasoning traces remain local.

Inference routing decisions should be configurable and enforceable by policy.

---

# Security Assumptions

The system must never assume that:

- the LLM is trustworthy,
- the LLM will follow prompt instructions,
- the LLM can enforce its own security boundaries.

All security guarantees must be provided by external enforcement mechanisms.

---

# Interaction with the Claw Architecture

## OpenClaw

Responsibilities:

- Task orchestration.
- Skill selection.
- Workflow coordination.

Restrictions:

- Cannot bypass OpenShell policy enforcement.
- Cannot directly access host resources.

## NemoClaw

Responsibilities:

- Reasoning and planning.
- Inference routing.
- Model selection.

Restrictions:

- Cannot override sandbox policies.
- Cannot directly modify infrastructure controls.

## OpenShell

Responsibilities:

- Secure execution environment.
- Policy enforcement.
- Resource isolation.
- Controlled tool execution.

OpenShell acts as the trust boundary between agent logic and the host environment.

---

# MCP Integration

The MCP receives:

```text
MuJoCo State
├── Object States
├── Environment State
├── Robot Arm State(s)
└── Future Multi-Robot State Support

UI Prompt
└── User Task Instruction
```

