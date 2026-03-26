# Solution Overview

This document describes the architecture decisions behind the appointment scheduling voice agent.

## Conversation Flow: Sequential vs Upfront Collection

We chose a **sequential flow**: the bot asks for name + date of birth first, validates the patient exists, and only then asks for appointment details.

The alternative was **upfront collection** -- gather all four fields (name, DOB, date, time) at once, then call both functions back-to-back. While faster in the happy path, this approach has a critical UX flaw: if the patient isn't found, you've wasted time collecting appointment details that are now useless. Worse, the user gets a failure message after a longer interaction, which feels more frustrating.

Sequential flow lets us fail fast and give actionable feedback ("I couldn't find you, want to try different details?") before asking for more information. In a voice interface, where corrections are slow and costly, this matters more than in a text UI.

## Framework: pipecat-flows vs Plain Function Calling

We use **pipecat-flows** (node-based conversation graph) rather than plain Pipecat function calling with `register_function` and system prompt instructions.

### Why not plain function calling?

With plain function calling, you define tools on the LLM and rely on a single system prompt to guide the conversation order. This works for simple cases, but has structural problems:

- **Prompt fragility**: The LLM must follow multi-step instructions purely from the system prompt. It can skip steps, ask for appointment details before verifying the patient, or call functions in the wrong order. The more complex the flow, the more the prompt has to compensate.
- **All tools always visible**: The LLM sees every registered function at every point in the conversation. There's no way to restrict which functions are available at which step, so the model has to "know" not to call `create_appointment` before `find_patient`.
- **Hard to extend**: Adding a new step (e.g., insurance verification) means rewriting the system prompt and hoping the LLM still follows the intended order.

### What pipecat-flows gives us

pipecat-flows models the conversation as a graph of nodes. Each node has its own system prompt (`task_messages`) and its own set of available functions. The framework handles transitions between nodes.

Concrete advantages:

- **Structural guarantees**: At the greeting node, the only available function is `find_patient`. The LLM literally cannot call `create_appointment` because it's not in the tool list. This eliminates an entire class of ordering bugs.
- **Simpler prompts**: Each node's prompt only needs to describe one step. No complex multi-step instructions, no "don't do X before Y" guardrails.
- **Clean separation of concerns**: Prompts, node definitions, and handler logic live in `prompts/scheduling.py`. The pipeline setup in `bot.py` just initializes the FlowManager. Adding a new step means adding a new node function, not touching the pipeline.
- **Explicit error handling per step**: The `patient_not_found` node has its own prompt and retry logic, rather than relying on the LLM to interpret a function return value correctly within a monolithic prompt.

### Trade-off

pipecat-flows adds a dependency and a small learning curve. For a two-step flow this might seem like overkill. We chose it anyway because the structural guarantees and per-node tool scoping eliminate real failure modes that would otherwise require extensive prompt engineering to mitigate -- and prompt engineering is never a guarantee.
