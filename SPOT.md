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

### As a user receiving LLM or CLI responses, I can...
- Have any LLM or CLI terminal response refined through an LLM pass that produces a succinct, accurate, matter-of-fact summary with natural filler words for spoken delivery
- Hear the refined response via audio (TTS) so I can consume results hands-free

### As a user researching documentation or content, I can...
- Ask a question and have the assistant parse multiple user-provided and/or LLM-selected documentation sources one at a time
- Have irrelevant sources automatically filtered out based on a configurable relevance threshold
- Receive a ranked shortlist of relevant sources — scored, prioritised, and each given a short description
- Hear a high-level audio summary of the shortlist for quick review before deciding which sources to explore further

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
10. **SF-10: Accurate refinement** — LLM response refinement preserves factual accuracy; no hallucinated content is introduced during the summarisation pass
11. **SF-11: Relevance-driven filtering** — Only sources scoring above the configured relevance threshold are surfaced; irrelevant material is discarded before ranking
12. **SF-12: Additive-only integration** — Phase 7 features are opt-in additions; disabling them has zero impact on existing Phases 1–6 behaviour
13. **SF-13: Voice-cloned TTS** — The assistant can speak with a user-supplied custom voice via Chatterbox TTS using a single WAV reference file

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
| R-13 | **File system operations** — Create a Typer command file with commands for: list directory, compare files (difflib), backup file, restore file. | R-12 | DONE |
| R-14 | **SQLite database CRUD** — Create a Typer command file with commands for: create table, insert row, query rows, update row, delete row. Operates on a configurable local `.db` file. | R-12 | DONE |
| R-15 | **JSON/YAML/CSV export** — Create a Typer command file with commands for: export query results or scratchpad data to JSON, YAML, or CSV format. Write output to a specified file path. | R-12, R-14 | DONE |

### Phase 7: LLM Response Refinement & Source Analysis Layer

> **Integration constraint:** Phase 7 features are strictly additive. They introduce new optional modules and config flags. They MUST NOT modify, override, or regress any module, function, or behaviour from Phases 1–6. All existing tests MUST continue to pass unmodified.

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-16 | **LLM response refinement via audio** — Create an optional post-processing pipeline that accepts any response (LLM reply or CLI stdout/stderr output) and passes it through an LLM refinement step. The refinement prompt MUST produce output that is: (a) succinct, (b) includes natural filler words suitable for spoken delivery, (c) factually accurate to the source response with no hallucinated additions, and (d) matter-of-fact in tone. The refined text is then delivered to the user via the existing TTS pipeline (R-07). Enable/disable via a new boolean flag in `assistant_config.yml` (e.g., `refinement.enabled`). When disabled, behaviour is identical to the current pipeline. | R-06, R-07, R-08 | DONE |
| R-17 | **Documentation source parsing, relevance filtering & ranked audio summary** — Create an optional source-analysis pipeline that: (1) accepts a user question plus a list of documentation or content sources (user-provided file paths/URLs and/or LLM-suggested sources), (2) parses each source individually extracting content relevant to the question, (3) scores each source for relevance against the user's question, (4) filters out any source scoring below a configurable relevance threshold (e.g., `source_analysis.relevance_threshold` in `assistant_config.yml`, default 0.5), (5) ranks remaining sources by relevance score in descending order, (6) generates a short description for each ranked source summarising its relevance, and (7) delivers a high-level audio summary of the ranked shortlist via TTS (R-07) so the user can decide which sources to review further. Enable/disable via a new boolean flag in `assistant_config.yml` (e.g., `source_analysis.enabled`). When disabled, no source analysis is performed and existing behaviour is unchanged. | R-01, R-04, R-06, R-07 | DONE |

### Phase 8: Chatterbox TTS Voice Cloning Layer

> **Integration constraint:** Phase 8 features are strictly additive. They extend the existing TTS abstraction layer (R-07) by registering a new provider. They MUST NOT modify, override, or regress any module, function, or behaviour from Phases 1–7. All existing tests MUST continue to pass unmodified.

#### Research Summary (2026-02-12)

**Package selected:** `chatterbox-tts` v0.1.6 — official Resemble AI pip package (MIT license).

**Why this package (not rsxdalv's fork branches):**
- rsxdalv (GitHub: [rsxdalv/chatterbox](https://github.com/rsxdalv/chatterbox)) maintains `fast` and `faster` fork branches with `torch.compile` + CUDA graph optimizations. These deliver measurable speedups but are **not published to PyPI** — they require `pip install -e .` from a git clone, introducing a fragile source dependency. The `fast` branch was referenced in a Reddit post about torch.compile improvements, and a GitHub user confirmed reading it but also reported broken imports after refactoring (TTS-WebUI issue #579). The `faster` branch focuses on multilingual (23-language) support rather than pure speed.
- rsxdalv's [TTS-WebUI](https://github.com/rsxdalv/TTS-WebUI) is a separate Gradio+React server with a Chatterbox extension. It works well on Windows (`.bat` launcher) and exposes an OpenAI-compatible API, but adds a heavy external server dependency unsuitable for our embedded-provider architecture.
- The official `chatterbox-tts` pip package includes **both** the original 0.5B model (voice cloning + emotion control) **and** Chatterbox-Turbo (350M, 1-step diffusion, ~6x faster than real-time). It is stable, version-pinned, and widely tested.

**Cross-validated user feedback:**
- **Quality:** 63.75% of blind evaluators preferred Chatterbox over ElevenLabs. Reddit r/LocalLLaMA users confirm "very decent" voice clones from 5–10s reference audio.
- **Speed (original model):** RTF ~0.68 on GTX 1080, ~0.5 on RTX 4090. First inference 4–12s (model loading), subsequent calls 1–3s for typical sentences. Reducing diffusion steps from 10 → 3 can cut mel generation from ~500ms → ~50ms with acceptable quality loss.
- **Speed (Turbo model):** ~6x real-time, sub-500ms first-chunk latency on RTX 4090. 350M params, 1-step diffusion. English-only, no emotion control, but supports paralinguistic tags (`[laugh]`, `[cough]`).
- **Windows:** Works natively (no WSL) on Python 3.11 with CUDA-enabled PyTorch. Known issue: slower than Linux on equivalent hardware (GitHub issue #127: i9 + RTX 3090 "does not run fast"). Python 3.12 has incomplete ML wheel support — **pin to 3.11**.
- **VRAM:** ~6.5–8 GB for original model, less for Turbo. RTX 3060+ (6 GB+) is minimum practical GPU.
- **Risks:** (1) Voice drift on inputs >1000 chars — mitigate by chunking text before TTS. (2) Occasional robotic artifacts — mitigate by allowing `exaggeration` and `cfg_weight` tuning in config. (3) First-call latency due to model download + load — mitigate via lazy loading with warm-up option.

**Decision:** Implement a `ChatterboxTTS` provider using the official pip package with support for both original and Turbo models, selectable via config. Custom WAV voice file path is a first-class config parameter.

#### Requirements

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-18 | **Chatterbox TTS provider** — Create a `ChatterboxTTS` class in `voice_agent/tts.py` that inherits from `TTSBackend`. The class MUST: (a) accept a `voice_file` config parameter pointing to a local `.wav` file used as the voice cloning reference, (b) accept a `model_type` config parameter (`"original"` or `"turbo"`, default `"original"`), (c) accept a `device` config parameter (`"cuda"`, `"cpu"`, or `"auto"`, default `"auto"` which selects CUDA if available), (d) lazy-load the Chatterbox model on first call to `stream_tts()` (following the `KokoroTTS` pattern), (e) implement `stream_tts(text) -> Iterator[tuple[int, Any]]` that generates audio using the reference voice file and yields `(sample_rate, audio_array)` tuples, (f) accept optional `exaggeration` (float, default 0.5) and `cfg_weight` (float, default 0.5) parameters for the original model to control emotion and pacing. Register the class as `"chatterbox"` in the `_PROVIDERS` registry. | R-07 | TODO |
| R-19 | **Chatterbox config schema** — Extend `assistant_config.yml` with a Chatterbox example in the `tts` section. The config MUST support: `provider: "chatterbox"`, `voice_file: "path/to/reference.wav"`, `model_type: "original"` or `"turbo"`, `device: "auto"`, `exaggeration: 0.5`, `cfg_weight: 0.5`. Add a commented-out Chatterbox config block below the active Kokoro config so users can switch by uncommenting. Document all parameters with inline YAML comments. | R-01, R-18 | TODO |
| R-20 | **Chatterbox dependency guard** — The `ChatterboxTTS` class MUST NOT import `chatterbox` at module level. Use lazy imports inside `stream_tts()` / `_load_model()` so that the rest of the application works without `chatterbox-tts` installed. If the import fails, raise a clear `RuntimeError` with the message: `"chatterbox-tts package not installed. Run: pip install chatterbox-tts"`. This ensures zero impact on users who don't need Chatterbox. | R-18 | TODO |
| R-21 | **Voice file validation** — Before loading the model, validate that: (a) `voice_file` path exists on disk, (b) the file has a `.wav` extension, (c) the file is readable and non-empty. Raise `FileNotFoundError` or `ValueError` with descriptive messages on failure. This prevents cryptic downstream errors from the Chatterbox library. | R-18 | TODO |
| R-22 | **Text chunking for long inputs** — If input text exceeds 500 characters, split it into sentence-boundary chunks (using Python's `re` module to split on `.!?` followed by whitespace) and process each chunk sequentially through Chatterbox, yielding audio tuples for each chunk. This mitigates the known voice-drift issue on long inputs. Chunks MUST NOT break mid-sentence. | R-18 | TODO |
| R-23 | **Chatterbox unit tests** — Add comprehensive tests to `tests/test_tts.py` covering: (a) `ChatterboxTTS` instantiation with default and custom parameters, (b) registration in `_PROVIDERS` under key `"chatterbox"`, (c) factory function `get_tts_backend()` returns `ChatterboxTTS` for `provider: "chatterbox"`, (d) voice file validation errors (missing file, wrong extension, empty file), (e) lazy import guard — verify `RuntimeError` when `chatterbox` package is unavailable (mock the import), (f) text chunking splits long text correctly and preserves sentence boundaries, (g) config parameter forwarding (`model_type`, `device`, `exaggeration`, `cfg_weight`, `voice_file`). All tests MUST mock the actual Chatterbox model to avoid GPU/download dependencies in CI. | R-18, R-20, R-21, R-22 | TODO |

#### Implementation Checklist (for the implementing session)

1. `pip install chatterbox-tts` in the project environment
2. Add `ChatterboxTTS` class to `voice_agent/tts.py` (~60–80 lines)
3. Register `"chatterbox"` in `_PROVIDERS` dict (1 line)
4. Add commented-out config block to `assistant_config.yml` (~10 lines)
5. Add voice file validation logic in `ChatterboxTTS.__init__()` or `_load_model()`
6. Add text chunking helper (private method or standalone function, ~15 lines)
7. Add tests to `tests/test_tts.py` (~80–100 lines, all mocked)
8. Run `pytest tests/ -v` — all existing + new tests must pass
9. Verify `local_voice_chat.py` and `local_voice_chat_advanced.py` still import and run
10. Update SPOT.md status column and revision log

#### Risk Mitigation Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `chatterbox-tts` not installed | App crash on import | Medium | Lazy import with clear error message (R-20) |
| WAV file missing or invalid | Cryptic Chatterbox error | High | Upfront validation with descriptive errors (R-21) |
| Voice drift on long text | Quality degradation | High | Sentence-boundary chunking at 500 chars (R-22) |
| No CUDA GPU available | Extremely slow inference | Medium | `device: "auto"` with CPU fallback + config override (R-18) |
| First-call latency (model download) | 30–60s hang on first use | High | Lazy loading (user sees delay only once); future: add warm-up CLI flag |
| Python 3.12 wheel incompatibility | Install failure | Medium | Document Python 3.11 requirement in config comments |
| VRAM exhaustion (< 6 GB GPU) | OOM crash | Low | Document minimum 6 GB VRAM; Turbo model uses less VRAM |
| Breaking changes in future chatterbox-tts versions | Provider stops working | Low | Pin `chatterbox-tts>=0.1.6,<0.2.0` if adding to requirements.txt |
| Existing TTS providers regressed | Test failures | Zero tolerance | Phase 8 is additive-only; no existing files modified except registry + config |

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
| 2026-02-12 | phase-6 | Phase 6 complete: file system operations with list/diff/backup/restore (R-13), SQLite CRUD with create/insert/query/update/delete (R-14), JSON/YAML/CSV export for query results and scratchpad (R-15) |
| 2026-02-12 | phase-7-spec | Phase 7 requirements added: LLM response refinement via audio (R-16), documentation source parsing with relevance filtering and ranked audio summary (R-17). Additive-only — no changes to Phases 1–6 |
| 2026-02-12 | phase-7 | Phase 7 complete: LLM response refinement pipeline with refinement_prompt template and config toggle (R-16), documentation source analysis pipeline with per-source relevance scoring, threshold filtering, ranked summary, and audio summary via source_relevance_prompt/source_summary_prompt templates (R-17). All 238 tests pass, zero regressions. Strictly additive — no Phases 1–6 files modified |
| 2026-02-12 | phase-8-spec | Phase 8 requirements added: Chatterbox TTS voice cloning provider (R-18–R-23). Research completed — official `chatterbox-tts` v0.1.6 pip package selected over rsxdalv fork branches (stability + PyPI availability). Cross-validated against GitHub issues, user benchmarks, and community feedback. Additive-only — no changes to Phases 1–7 |
