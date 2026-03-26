---
date: 2026-03-27T00:00:00Z
planner: claude
branch: main
repository: healthie-agent
topic: "Implement scheduling conversation flow using pipecat-flows"
tags: [plan, conversation-flow, pipecat-flows, scheduling]
status: draft
autonomy: critical
last_updated: 2026-03-27
last_updated_by: claude
research_refs:
  - thoughts/shared/research/20260327_how-the-bot-works.md
---

# Plan: Implement Scheduling Conversation Flow

**Date**: 2026-03-27
**Scope**: Conversation flow only (not Healthie tool call implementations)
**Approach**: pipecat-flows (node-based conversation graph), sequential flow

## Overview

Add a structured conversation flow so the bot:
1. Greets the patient and asks for their **name** and **date of birth**
2. Calls `find_patient` to look up the patient
3. If found, asks for the desired **appointment date and time**
4. Calls `create_appointment` to book the appointment
5. Confirms the booking or handles errors gracefully

All prompts/node definitions live in `prompts/scheduling.py`. The `bot.py` changes are minimal: import FlowManager, wire it up, remove the old hardcoded prompt.

## Architecture

```
prompts/scheduling.py          # Node definitions, system prompts, tool schemas, handlers
bot.py                         # Pipeline setup, FlowManager initialization
healthie.py                    # Healthie API calls (unchanged in this plan)
```

### Conversation Graph

```
[greeting_node] ──find_patient──> [appointment_node] ──create_appointment──> [confirmation_node]
       │                                  │                                         │
       └── patient not found ─┐           └── booking failed ─┐                    └── end
                               │                                │
                               └── retry / end                  └── retry / end
```

---

## Phase 1: Add pipecat-ai-flows dependency

**Files**: `pyproject.toml`

### Steps

1.1. Add `pipecat-ai-flows` to the project dependencies in `pyproject.toml`:
   ```toml
   dependencies = [
       ...,
       "pipecat-ai-flows",
   ]
   ```

1.2. Run `uv sync` to install the new dependency.

### Verification
- `uv run python -c "from pipecat_flows import FlowManager; print('OK')"` succeeds

---

## Phase 2: Create `prompts/scheduling.py`

**Files**: `prompts/__init__.py` (empty), `prompts/scheduling.py` (new)

This file owns all conversation flow logic: node definitions, system prompts, tool schemas, and handler functions.

### Steps

2.1. Create `prompts/__init__.py` (empty file to make it a package).

2.2. Create `prompts/scheduling.py` with the following structure:

```python
"""Scheduling conversation flow using pipecat-flows.

Defines the node graph for the appointment scheduling conversation:
  greeting_node -> appointment_node -> confirmation_node
"""

from pipecat_flows import FlowArgs, FlowManager, FlowsFunctionSchema, NodeConfig

from healthie import find_patient, create_appointment


# --- Role message (persistent across all nodes) ---

ROLE_MESSAGES = [
    {
        "role": "system",
        "content": (
            "You are a friendly and professional digital assistant for the Prosper Health clinic. "
            "You help patients schedule appointments. Be warm, conversational, and concise. "
            "Always confirm information back to the patient before proceeding."
        ),
    }
]


# --- Node definitions ---

def create_greeting_node() -> NodeConfig:
    """Initial node: greet patient, ask for name and date of birth."""
    return {
        "role_messages": ROLE_MESSAGES,
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Greet the patient warmly and introduce yourself as a digital assistant "
                    "from the Prosper Health clinic. Tell them you can help schedule an appointment. "
                    "Ask for their full name and date of birth so you can look them up in the system. "
                    "You must collect BOTH the name and date of birth before calling the function."
                ),
            }
        ],
        "functions": [
            FlowsFunctionSchema(
                name="find_patient",
                description="Look up a patient by name and date of birth",
                properties={
                    "name": {
                        "type": "string",
                        "description": "The patient's full name",
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "The patient's date of birth in YYYY-MM-DD format",
                    },
                },
                required=["name", "date_of_birth"],
                handler=handle_find_patient,
            )
        ],
    }


def create_appointment_node() -> NodeConfig:
    """Second node: ask for appointment date and time."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "The patient has been found in the system. Now ask them for their preferred "
                    "appointment date and time. Once they provide both, create the appointment. "
                    "Be flexible with how they express dates and times, but confirm the exact "
                    "date and time before proceeding."
                ),
            }
        ],
        "functions": [
            FlowsFunctionSchema(
                name="create_appointment",
                description="Create an appointment for the patient",
                properties={
                    "date": {
                        "type": "string",
                        "description": "The appointment date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "description": "The appointment time in HH:MM format (24-hour)",
                    },
                },
                required=["date", "time"],
                handler=handle_create_appointment,
            )
        ],
    }


def create_confirmation_node() -> NodeConfig:
    """Final node: confirm booking and say goodbye."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "The appointment has been booked. Summarize the appointment details "
                    "(patient name, date, and time) back to the patient. Ask if there's "
                    "anything else you can help with. If not, say goodbye warmly."
                ),
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


def create_patient_not_found_node() -> NodeConfig:
    """Error node: patient not found, offer to retry or end."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "The patient was not found in the system. Apologize and ask if they'd like "
                    "to try again with different details. If they want to retry, ask for their "
                    "name and date of birth again."
                ),
            }
        ],
        "functions": [
            FlowsFunctionSchema(
                name="find_patient",
                description="Look up a patient by name and date of birth",
                properties={
                    "name": {
                        "type": "string",
                        "description": "The patient's full name",
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "The patient's date of birth in YYYY-MM-DD format",
                    },
                },
                required=["name", "date_of_birth"],
                handler=handle_find_patient,
            )
        ],
    }


# --- Handler functions ---

async def handle_find_patient(args: FlowArgs, flow_manager: FlowManager):
    """Handle the find_patient tool call. Transitions to appointment or not-found node."""
    name = args["name"]
    date_of_birth = args["date_of_birth"]

    result = await find_patient(name, date_of_birth)

    if result:
        flow_manager.state["patient_id"] = result["patient_id"]
        flow_manager.state["patient_name"] = result["name"]
        return (
            f"Patient found: {result['name']}.",
            create_appointment_node(),
        )
    else:
        return (
            "No patient found with that name and date of birth.",
            create_patient_not_found_node(),
        )


async def handle_create_appointment(args: FlowArgs, flow_manager: FlowManager):
    """Handle the create_appointment tool call. Transitions to confirmation node."""
    patient_id = flow_manager.state["patient_id"]
    date = args["date"]
    time = args["time"]

    result = await create_appointment(patient_id, date, time)

    if result:
        flow_manager.state["appointment"] = result
        return (
            f"Appointment created for {date} at {time}.",
            create_confirmation_node(),
        )
    else:
        return (
            "Sorry, there was an issue creating the appointment. Please try a different date or time.",
            None,  # Stay on appointment node to retry
        )
```

### Key design decisions
- **ROLE_MESSAGES** is defined once and set in the greeting node; pipecat-flows persists it across transitions.
- **Handlers import and call `healthie.find_patient` / `healthie.create_appointment` directly** -- this is the bridge between the conversation flow and the Healthie integration. When the stubs are implemented later, the flow will work end-to-end without changes.
- **`patient_not_found_node`** reuses the same `find_patient` tool schema, allowing the patient to retry.
- **`create_confirmation_node`** has no functions and uses `post_actions: end_conversation` to cleanly close the session.

### Verification
- File imports without errors: `uv run python -c "from prompts.scheduling import create_greeting_node; print('OK')"`
- With dummy healthie implementations (Phase 4), full flow is testable end-to-end

---

## Phase 3: Modify `bot.py` to use FlowManager

**Files**: `bot.py`

### Steps

3.1. **Add imports** (after existing imports, around line 59):
```python
from pipecat_flows import FlowManager
from prompts.scheduling import create_greeting_node
```

3.2. **Remove the old hardcoded system prompt** (lines 79-84):
```python
# DELETE these lines:
messages = [
    {
        "role": "system",
        "content": "You are a friendly AI assistant. Respond naturally and keep your answers conversational.",
    },
]
```

3.3. **Remove old context creation** (line 86):
```python
# DELETE this line:
context = LLMContext(messages)
```

3.4. **Replace with FlowManager-compatible context** -- the `LLMContextAggregatorPair` still needs a context, but FlowManager will manage the messages. Create an empty context:
```python
context = LLMContext()
```

3.5. **Create FlowManager after task creation** (after line 118):
```python
flow_manager = FlowManager(
    task=task,
    llm=llm,
    context_aggregator=assistant_aggregator,
    transport=transport,
)
```

Note: `context_aggregator` should be the **assistant_aggregator** based on pipecat-flows examples.

3.6. **Replace the on_client_connected handler** (lines 120-125):
```python
# REPLACE:
@transport.event_handler("on_client_connected")
async def on_client_connected(transport, client):
    logger.info(f"Client connected")
    messages.append({"role": "system", "content": "Say hello and briefly introduce yourself as a digital assistant from the Prosper Health clinic."})
    await task.queue_frames([LLMRunFrame()])

# WITH:
@transport.event_handler("on_client_connected")
async def on_client_connected(transport, client):
    logger.info(f"Client connected")
    await flow_manager.initialize(create_greeting_node())
```

3.7. **Clean up unused imports** -- remove `LLMRunFrame` from the frames import if no longer used elsewhere.

### Summary of bot.py changes
- **Added**: 2 import lines
- **Removed**: ~7 lines (old messages, old LLMContext creation, old on_connect body)
- **Modified**: ~5 lines (empty LLMContext, FlowManager creation, on_connect handler)
- **Net change**: ~14 lines touched

### Verification
- Bot starts without errors: `uv run bot.py`
- On browser connect, bot greets patient and asks for name + DOB
- (Full end-to-end test requires healthie.py implementations)

---

## Phase 4: Make healthie.py functions async with dummy implementations

**Files**: `healthie.py`

### Context
The current `find_patient` and `create_appointment` stubs are synchronous (`def`, not `async def`) with `pass` bodies that return `None`. We need to:
1. Make them `async` so the pipecat-flows handlers can `await` them
2. Add dummy implementations that return hardcoded data so the full conversation flow is testable end-to-end

The dummy implementations will be replaced with real Healthie/Playwright calls in a future PR.

### Steps

4.1. Replace `find_patient` stub (line ~76) with a dummy async implementation:
```python
async def find_patient(name, date_of_birth):
    """Look up a patient by name and date of birth.

    Args:
        name: The patient's full name.
        date_of_birth: The patient's date of birth (YYYY-MM-DD).

    Returns:
        dict with patient_id, name, date_of_birth if found, or None.
    """
    # TODO: Replace with real Healthie lookup via Playwright
    return {"patient_id": "dummy-123", "name": name, "date_of_birth": date_of_birth}
```

4.2. Replace `create_appointment` stub (line ~105) with a dummy async implementation:
```python
async def create_appointment(patient_id, date, time):
    """Create an appointment for a patient.

    Args:
        patient_id: The patient's ID from find_patient.
        date: The appointment date (YYYY-MM-DD).
        time: The appointment time (HH:MM, 24-hour).

    Returns:
        dict with appointment_id, patient_id, date, time if created, or None.
    """
    # TODO: Replace with real Healthie appointment creation via Playwright
    return {"appointment_id": "appt-456", "patient_id": patient_id, "date": date, "time": time}
```

### Design notes
- The dummy implementations always succeed, which means the happy path (greeting → appointment → confirmation) is fully testable.
- The return format serves as a **living contract** for what the real implementations must return -- the flow handlers depend on these keys (`patient_id`, `name`, `appointment_id`, etc.).
- The `# TODO` comments make it clear these are placeholders.

### Verification
- `uv run python -c "import asyncio; from healthie import find_patient; print(asyncio.run(find_patient('Jane Doe', '1990-01-15')))"` returns `{'patient_id': 'dummy-123', 'name': 'Jane Doe', 'date_of_birth': '1990-01-15'}`
- Full end-to-end test: start bot, connect via browser, provide name + DOB → bot finds patient → provide date + time → bot confirms appointment

---

## Files Changed Summary

| File | Change | Lines |
|------|--------|-------|
| `pyproject.toml` | Add `pipecat-ai-flows` dependency | ~1 |
| `prompts/__init__.py` | New empty file | 0 |
| `prompts/scheduling.py` | New file: nodes, prompts, handlers | ~150 |
| `bot.py` | Wire FlowManager, remove old prompt | ~14 |
| `healthie.py` | Make async + dummy implementations | ~10 |

**Total new code**: ~150 lines (prompts/scheduling.py)
**Total modified code**: ~24 lines across bot.py + healthie.py

## Open Questions

1. **FlowManager `context_aggregator` parameter**: The research suggests passing the assistant_aggregator, but some examples pass a different aggregator. Need to verify at implementation time.
2. **`post_actions: end_conversation`**: Need to confirm this action type exists in the installed version of pipecat-flows. If not, we can remove it and let the conversation end naturally.
3. **Healthie function return format**: The handlers assume `find_patient` returns `{"patient_id": ..., "name": ...}` and `create_appointment` returns a dict. The dummy implementations now define this contract explicitly.
