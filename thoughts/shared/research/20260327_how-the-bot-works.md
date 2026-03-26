---
date: 2026-03-27T00:00:00Z
researcher: claude
git_commit: 1c3bebb
branch: main
repository: healthie-agent
topic: "How does the current bot work?"
tags: [research, codebase, pipecat, voice-bot, healthie, playwright]
status: complete
autonomy: critical
last_updated: 2026-03-27
last_updated_by: claude
---

# Research: How Does the Current Bot Work?

**Date**: 2026-03-27
**Researcher**: Claude
**Git Commit**: 1c3bebb
**Branch**: main

## Research Question
How does the current bot work? What is its architecture, conversation flow, and integration points?

## Summary

The healthie-agent is a **real-time voice AI assistant** built on the **Pipecat** framework, designed to schedule appointments for the Prosper Health clinic by interacting with **Healthie**, a healthcare EHR system. It uses **ElevenLabs** for both speech-to-text and text-to-speech, **OpenAI** for the conversational LLM, and **WebRTC (via Daily)** for real-time audio transport. A web interface is served locally on port 7860.

The bot is currently in a **partially implemented state**: it can greet users and hold a basic conversation, but it **cannot yet find patients or create appointments**. The `healthie.py` module provides only a working login function via Playwright browser automation; the `find_patient` and `create_appointment` functions are stubs. Additionally, `bot.py` does not import or reference `healthie.py` at all — no function-calling/tool-use is configured on the LLM.

## Detailed Findings

### Entry Point & Pipeline (`bot.py`)

The bot is a single-file Pipecat application. When run (`uv run bot.py`), it:

1. Loads environment variables via `dotenv` (`bot.py:22-23`)
2. Creates a WebRTC transport via `create_transport()` (`bot.py:140-150`)
3. Initializes three AI services (`bot.py:70-77`):
   - **STT**: `ElevenLabsRealtimeSTTService` — real-time speech recognition
   - **TTS**: `ElevenLabsTTSService` — voice synthesis (voice ID `SAz9YHcvj6GT2YYXdXww` hardcoded)
   - **LLM**: `OpenAILLMService` — conversation engine (no tools/functions configured)
4. Builds an 8-stage linear audio pipeline (`bot.py:98-109`):
   ```
   transport.input → RTVI → STT → user_aggregator → LLM → TTS → transport.output → assistant_aggregator
   ```
5. On client WebRTC connect, sends a greeting prompt and triggers the LLM (`bot.py:124`)

### System Prompt & Conversation Flow (`bot.py:79-84`)

The LLM receives a minimal system prompt:
> "You are a friendly AI assistant. Respond naturally and keep your answers conversational."

On connection, a second message is appended:
> "Say hello and briefly introduce yourself as a digital assistant from the Prosper Health clinic."

There is **no function calling, no tool definitions, and no structured conversation flow** (e.g., asking for patient name/DOB or appointment details). The bot currently just holds free-form conversation.

### Turn-Taking & VAD (`bot.py:87-94`)

Turn detection uses `LocalSmartTurnAnalyzerV3` wrapped in `TurnAnalyzerUserTurnStopStrategy`. Voice Activity Detection uses `SileroVADAnalyzer` with a 0.2-second stop threshold (`bot.py:144`), meaning the bot considers the user done speaking after 0.2s of silence.

### Healthie Integration (`healthie.py`)

All Healthie interaction is via **Playwright headless Chromium** browser automation — no REST/GraphQL API calls.

#### `login_to_healthie()` — IMPLEMENTED (`healthie.py:16-73`)
- Reads `HEALTHIE_EMAIL` and `HEALTHIE_PASSWORD` from environment
- Launches headless Chromium, navigates to `https://secure.gethealthie.com/users/sign_in`
- Fills email/password fields, clicks "Log In", waits 3 seconds
- Validates login by checking if URL still contains "sign_in"
- Stores browser/page as module-level singletons for session reuse (`healthie.py:12-13`)

#### `find_patient(name, date_of_birth)` — STUB (`healthie.py:76-102`)
- Documented to return `dict` with `patient_id`, `name`, `date_of_birth` or `None`
- Body is `pass` with TODO comments

#### `create_appointment(patient_id, date, time)` — STUB (`healthie.py:105-135`)
- Documented to return `dict` with `appointment_id`, `patient_id`, `date`, `time` or `None`
- Body is `pass` with TODO comments

### Project Configuration

- **Python >= 3.10** with `uv` package manager
- **Key dependencies** (`pyproject.toml`): `pipecat-ai[webrtc,daily,silero,elevenlabs,openai,local-smart-turn-v3,runner]`, `playwright`
- **Docker** uses `dailyco/pipecat-base:latest` base image; only copies `bot.py` (not `healthie.py`)
- **Dev tools**: `pyright` (type checking), `ruff` (linting, import sorting only)

### Environment Variables

| Variable | Used By | Purpose |
|---|---|---|
| `ELEVENLABS_API_KEY` | `bot.py` | STT & TTS |
| `OPENAI_API_KEY` | `bot.py` | LLM |
| `HEALTHIE_EMAIL` | `healthie.py` | Healthie login |
| `HEALTHIE_PASSWORD` | `healthie.py` | Healthie login |

## Code References

| File | Line | Description |
|------|------|-------------|
| `bot.py` | 70-77 | Service initialization (STT, TTS, LLM) |
| `bot.py` | 79-84 | System prompt definition |
| `bot.py` | 87-94 | Turn-taking configuration |
| `bot.py` | 98-109 | Pipeline assembly (8-stage) |
| `bot.py` | 124 | On-connect greeting trigger |
| `bot.py` | 140-150 | WebRTC transport & server setup |
| `bot.py` | 153-156 | Main entry point |
| `healthie.py` | 12-13 | Module-level browser/page singletons |
| `healthie.py` | 16-73 | Login implementation (Playwright) |
| `healthie.py` | 76-102 | find_patient stub |
| `healthie.py` | 105-135 | create_appointment stub |

## Architecture Documentation

```
┌─────────────────────────────────────────────────────┐
│                   Browser (localhost:7860)           │
│                   WebRTC Client                      │
└─────────────┬───────────────────────┬───────────────┘
              │ audio in              │ audio out
              ▼                       ▲
┌─────────────────────────────────────────────────────┐
│                 Pipecat Pipeline                     │
│                                                      │
│  transport.input                                     │
│       │                                              │
│       ▼                                              │
│  RTVI Processor                                      │
│       │                                              │
│       ▼                                              │
│  ElevenLabs STT  ──→  User Aggregator               │
│                              │                       │
│                              ▼                       │
│                     OpenAI LLM (no tools)            │
│                              │                       │
│                              ▼                       │
│                     ElevenLabs TTS                    │
│                              │                       │
│                              ▼                       │
│                     transport.output                  │
│                              │                       │
│                              ▼                       │
│                   Assistant Aggregator                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│           healthie.py (NOT CONNECTED)                │
│                                                      │
│  login_to_healthie()  ✅ Implemented                 │
│  find_patient()       ❌ Stub                        │
│  create_appointment() ❌ Stub                        │
│                                                      │
│  Uses: Playwright → Chromium → Healthie Web UI       │
└─────────────────────────────────────────────────────┘
```

### What's Missing (per README expectations)

1. **Conversation flow**: Bot needs to ask for patient name, DOB, then appointment date/time
2. **Function calling**: LLM needs tool definitions to trigger `find_patient` and `create_appointment`
3. **find_patient implementation**: Playwright automation to search patients in Healthie
4. **create_appointment implementation**: Playwright automation to create appointments in Healthie
5. **Integration**: `bot.py` must import and wire `healthie.py` functions as LLM tools

## Historical Context (from thoughts/)
No prior research documents found in thoughts/ directory.

## Related Research
None — this is the first research document.

## Open Questions
- Should the Healthie integration use the Healthie GraphQL API instead of (or in addition to) Playwright browser automation?
- What specific Pipecat function-calling patterns should be used to wire the healthie functions as LLM tools?
- Is the Dockerfile intentionally missing `healthie.py`? This would need to be added for deployment.
