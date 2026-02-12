# SPOT: Single Point of Truth

## North Star

A fully local, privacy-first, voice AI assistant that listens, understands, remembers, and acts on your behalf — executing real commands across your system through natural speech, with swappable AI backends and zero cloud dependency.

---

## End-User Outcomes

### As a conversational assistant user, I can...
- Speak naturally and receive fast, streaming audio responses via WebRTC (browser or phone)
- Have multi-turn conversations where the assistant remembers what we discussed in this session
- Resume context across sessions through persistent scratchpad memory
- Feed the assistant reference documents so it makes better decisions about my specific projects
- Choose between a casual chat mode and a power-user agentic command mode

### As a power user, I can...
- Issue voice commands that the assistant translates into real CLI commands and executes
- Chain multiple commands together in a single voice instruction
- Extend the assistant's capabilities by simply writing new Typer command files
- Query and manipulate SQLite databases through voice
- Perform file system operations (list, compare, backup, restore) hands-free
- Export data in JSON, YAML, or CSV formats through voice commands

### As a developer/operator, I can...
- Swap LLM backends (Ollama models, DeepSeek, Claude, etc.) via a single config file
- Swap TTS backends (Kokoro, pyttsx3, RealtimeTTS) via config
- Define assistant personas, names, and behaviour through YAML configuration
- Structure and version-control prompt templates as XML files
- Run the entire stack 100% locally with no cloud API keys required
- Optionally connect cloud backends for higher quality when desired

---

## Success Factors

1. **SF-01: Sub-5s end-to-end latency** — From end of speech to start of audio response in fully-local mode
2. **SF-02: Zero cloud dependency** — Every feature works fully offline with local models
3. **SF-03: Stateful conversations** — The assistant maintains context within and across sessions
4. **SF-04: Safe command execution** — Generated commands are validated before execution; user retains control
5. **SF-05: Single config, full control** — One YAML file governs all backend, voice, and persona settings
6. **SF-06: Extensible by design** — New voice commands are added by dropping in a Typer Python file
7. **SF-07: Test-driven quality** — Every feature has tests; all must pass before any commit
8. **SF-08: No regression** — Existing FastRTC/WebRTC/phone functionality remains intact throughout
9. **SF-09: Clean separation** — Conversational mode and agentic mode are distinct, composable pipelines

---

## Requirements

### Phase 1: Foundation Layer

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-01 | **YAML config file** — Create `assistant_config.yml` with sections for: assistant name, human name, STT engine, LLM backend (provider + model), TTS backend (provider + voice), mode (chat/agent). Create a config loader module that provides dot-path access (e.g., `config.llm.provider`). | — | DONE |
| R-02 | **Conversation history** — Maintain a list of `{role, content}` messages for the current session. Pass full history to the LLM on each turn. Clear on session restart. Cap at configurable max turns to prevent context overflow. | R-01 | DONE |
| R-03 | **Scratchpad persistent memory** — Create a `scratchpad.md` file the LLM can read from and write to across sessions. Expose read/write as utility functions. Inject scratchpad contents into the LLM prompt when non-empty. | R-01 | DONE |

### Phase 2: Prompt & Context Layer

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-04 | **Context files** — Accept a `--context-files` CLI argument (list of file paths). Read file contents at startup and inject them into the LLM system prompt as reference material. | R-01 | DONE |
| R-05 | **XML prompt templates** — Create a `prompts/` directory with XML template files for: system prompt, agentic command prompt, concise response prompt. Build a template loader that reads and interpolates variables (assistant name, commands, scratchpad, context, user input). | R-01 | DONE |

### Phase 3: Multi-Backend Layer

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-06 | **Multiple LLM backends** — Create an LLM abstraction layer with a common interface (`chat(messages) -> str`). Implement providers for: Ollama (local), DeepSeek API, Anthropic Claude API. Provider and model are selected via `assistant_config.yml`. Ollama is the default. | R-01 | DONE |
| R-07 | **Multiple TTS backends** — Create a TTS abstraction layer with a common interface (`stream_tts(text) -> Iterator[audio_chunk]`). Implement providers for: Kokoro (current, default), pyttsx3 (local fallback), RealtimeTTS/SystemEngine. Provider is selected via `assistant_config.yml`. | R-01 | DONE |

### Phase 4: Mode Architecture

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-08 | **Two assistant modes** — Implement a `chat` mode (conversational, current behaviour enhanced with history/memory) and an `agent` mode (agentic command execution). Mode is set in config. Both modes share the same STT/TTS/LLM backends. Each mode has its own prompt pipeline. The main entry point selects the appropriate handler based on config. | R-01, R-05, R-06, R-07 | DONE |

### Phase 5: Agentic Execution Layer

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-09 | **Subprocess execution** — Create an `execute.py` module that runs shell commands via `subprocess.run()`. Capture stdout/stderr. Return structured results `{success, stdout, stderr, return_code}`. Enforce a configurable timeout. | — | DONE |
| R-10 | **Voice-to-CLI command generation** — In agent mode, the LLM receives the user transcript + available Typer commands + prompt template, and outputs a valid Typer CLI command string. Parse and validate the output before execution. | R-05, R-08, R-09 | DONE |
| R-11 | **Command chaining** — Support `&&`-separated commands in LLM output. Execute sequentially; halt on first failure. Return combined results. | R-10 | DONE |
| R-12 | **Extensible command surface** — Accept a `--typer-file` CLI argument pointing to a Python file containing Typer commands. Parse the file to extract command signatures and docstrings. Inject the command catalog into the LLM prompt so it can discover available commands automatically. | R-05, R-10 | DONE |

### Phase 6: Built-in Command Library

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-13 | **File system operations** — Create a Typer command file with commands for: list directory, compare files (difflib), backup file, restore file. | R-12 | TODO |
| R-14 | **SQLite database CRUD** — Create a Typer command file with commands for: create table, insert row, query rows, update row, delete row. Operates on a configurable local `.db` file. | R-12 | TODO |
| R-15 | **JSON/YAML/CSV export** — Create a Typer command file with commands for: export query results or scratchpad data to JSON, YAML, or CSV format. Write output to a specified file path. | R-12, R-14 | TODO |

---

## Quality Gateway

Every commit MUST pass ALL of the following before being pushed:

1. **Unit tests pass** — `pytest tests/ -v` exits 0
2. **No regressions** — Existing `local_voice_chat.py` and `local_voice_chat_advanced.py` remain functional
3. **Config validation** — If config changes were made, the config loader test suite passes
4. **Import check** — All new modules import without error
5. **Type check** — No new type errors introduced (if type checking is configured)
6. **SPOT alignment** — This document is updated with current status after every commit

---

## Revision Log

| Date | Commit | Changes |
|------|--------|---------|
| 2026-02-12 | _initial_ | SPOT document created with 15 requirements across 6 phases |
| 2026-02-12 | phase-1 | Phase 1 complete: YAML config (R-01), conversation history (R-02), scratchpad memory (R-03) |
| 2026-02-12 | phase-2 | Phase 2 complete: context files CLI (R-04), XML prompt templates with loader (R-05) |
| 2026-02-12 | phase-3 | Phase 3 complete: LLM abstraction layer with Ollama/DeepSeek/Anthropic providers (R-06), TTS abstraction layer with Kokoro/pyttsx3/RealtimeTTS providers (R-07) |
| 2026-02-12 | phase-4 | Phase 4 complete: dual mode architecture with ChatMode and AgentMode handlers, factory pattern, mode-specific prompt pipelines (R-08) |
| 2026-02-12 | phase-5 | Phase 5 complete: subprocess execution with timeout (R-09), voice-to-CLI command parser with validation (R-10), &&-command chaining (R-11), Typer file discovery and catalog generation (R-12) |
