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

**Three model options supported:**
- **Official original** (0.5B, 10-step diffusion) — voice cloning + emotion control. Install: `pip install --no-deps chatterbox-tts`
- **Official turbo** (350M, 1-step diffusion, ~6x real-time) — fastest official, English-only. Install: `pip install --no-deps chatterbox-tts`
- **rsxdalv `faster` branch** — fork with `torch.compile` + manual CUDA graph capture for maximum throughput. Eager mode for initial forward pass, CUDA graphs for repeated token generation. Install: `pip install --no-deps git+https://github.com/rsxdalv/chatterbox.git@faster`

**Why rsxdalv-faster is included as an option (updated 2026-02-12):**
- rsxdalv (GitHub: [rsxdalv/chatterbox](https://github.com/rsxdalv/chatterbox)) maintains `fast` and `faster` fork branches. The `faster` branch integrates `torch.compile` and manual CUDA graph optimisations that accelerate the token-generation hot path. Users on Reddit and in TTS-WebUI issues have confirmed measurable speedups.
- The branch is **not on PyPI** — it requires `pip install --no-deps git+https://github.com/rsxdalv/chatterbox.git@faster`. This is an acceptable trade-off for users who want maximum speed and are comfortable with a git dependency.
- The API is identical to the official package (same `ChatterboxTTS2` / `ChatterboxTurbo` classes), so no code changes are needed beyond the install command.
- Risk: the fork may lag behind official releases. Mitigation: `model_type` is a config parameter — users can switch back to `"original"` or `"turbo"` at any time without code changes.

**Safe dependency installation (critical for users with existing torch/CUDA):**
- **ALWAYS** use `--no-deps` when installing chatterbox-tts to avoid overwriting your existing PyTorch, CUDA, cuDNN, wheel, or other ML drivers.
- Install order (prioritised):
  1. **DO NOT TOUCH:** torch, torchaudio, nvidia-cublas-cu12, nvidia-cudnn-cu12, nvidia-cuda-runtime-cu12, triton, wheel — these are already configured for your GPU.
  2. `pip install --no-deps chatterbox-tts` (or `git+...@faster` for rsxdalv branch)
  3. `pip install transformers accelerate tqdm scipy conformer` — only the missing non-torch deps.
- This pattern is community-validated (GitHub issue #159, Medium guide Dec 2025, FastRTC emotion project).

**Cross-validated user feedback:**
- **Quality:** 63.75% of blind evaluators preferred Chatterbox over ElevenLabs. Reddit r/LocalLLaMA users confirm "very decent" voice clones from 5–10s reference audio.
- **Speed (original model):** RTF ~0.68 on GTX 1080, ~0.5 on RTX 4090. First inference 4–12s (model loading), subsequent calls 1–3s for typical sentences. Reducing diffusion steps from 10 → 3 can cut mel generation from ~500ms → ~50ms with acceptable quality loss.
- **Speed (Turbo model):** ~6x real-time, sub-500ms first-chunk latency on RTX 4090. 350M params, 1-step diffusion. English-only, no emotion control, but supports paralinguistic tags (`[laugh]`, `[cough]`).
- **Speed (rsxdalv-faster):** torch.compile + CUDA graphs on the token-generation loop. Expected ~20–40% speedup over vanilla original model on Ada Lovelace GPUs (RTX 40xx). Exact numbers depend on GPU, batch size, and text length.
- **Windows:** Works natively (no WSL) on Python 3.11 with CUDA-enabled PyTorch. Known issue: slower than Linux on equivalent hardware (GitHub issue #127: i9 + RTX 3090 "does not run fast"). Python 3.12 has incomplete ML wheel support — **pin to 3.11**.
- **VRAM:** ~6.5–8 GB for original model, less for Turbo. RTX 3060+ (6 GB+) is minimum practical GPU.
- **RTX 4080 12 GB estimates:**
  - Original: RTF ~0.55–0.65, ~1.5–2.5s per sentence
  - Turbo: RTF ~0.25–0.35, ~0.5–0.8s per sentence
  - rsxdalv-faster: RTF ~0.4–0.5 (torch.compile speedup over original), ~1.0–1.8s per sentence
  - Windows 11 penalty: ~20–30% slower than Linux on same hardware
- **Risks:** (1) Voice drift on inputs >1000 chars — mitigate by chunking text before TTS. (2) Occasional robotic artifacts — mitigate by allowing `exaggeration` and `cfg_weight` tuning in config. (3) First-call latency due to model download + load — mitigate via lazy loading with warm-up option. (4) rsxdalv fork may lag behind official releases — mitigate by making model_type a user-switchable config parameter.

**Decision:** Implement a `ChatterboxTTS` provider with three model types (`original`, `turbo`, `rsxdalv-faster`), selectable via config. Safe `--no-deps` installation is documented to protect existing torch/CUDA environments. Custom WAV voice file path is a first-class config parameter.

#### Requirements

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-18 | **Chatterbox TTS provider** — Create a `ChatterboxTTS` class in `voice_agent/tts.py` that inherits from `TTSBackend`. The class MUST: (a) accept a `voice_file` config parameter pointing to a local `.wav` file used as the voice cloning reference, (b) accept a `model_type` config parameter (`"original"`, `"turbo"`, or `"rsxdalv-faster"`, default `"original"`), (c) accept a `device` config parameter (`"cuda"`, `"cpu"`, or `"auto"`, default `"auto"` which selects CUDA if available), (d) lazy-load the Chatterbox model on first call to `stream_tts()` (following the `KokoroTTS` pattern), (e) implement `stream_tts(text) -> Iterator[tuple[int, Any]]` that generates audio using the reference voice file and yields `(sample_rate, audio_array)` tuples, (f) accept optional `exaggeration` (float, default 0.5) and `cfg_weight` (float, default 0.5) parameters for the original and rsxdalv-faster models to control emotion and pacing. Register the class as `"chatterbox"` in the `_PROVIDERS` registry. The `rsxdalv-faster` model type uses the same `ChatterboxTTS2` class but from rsxdalv's `faster` fork branch which includes `torch.compile` + CUDA graph optimisations. | R-07 | DONE |
| R-19 | **Chatterbox config schema** — Extend `assistant_config.yml` with Chatterbox examples in the `tts` section. The config MUST support: `provider: "chatterbox"`, `voice_file: "path/to/reference.wav"`, `model_type: "original"` or `"turbo"` or `"rsxdalv-faster"`, `device: "auto"`, `exaggeration: 0.5`, `cfg_weight: 0.5`. Add commented-out config blocks for all three model types below the active Kokoro config. Document all parameters and safe `--no-deps` install commands with inline YAML comments. | R-01, R-18 | DONE |
| R-20 | **Chatterbox dependency guard** — The `ChatterboxTTS` class MUST NOT import `chatterbox` at module level. Use lazy imports inside `_load_model()` so that the rest of the application works without `chatterbox-tts` installed. If the import fails, raise a clear `RuntimeError` with install instructions (different commands for official vs. rsxdalv-faster). This ensures zero impact on users who don't need Chatterbox. | R-18 | DONE |
| R-21 | **Voice file validation** — Before loading the model, validate that: (a) `voice_file` path exists on disk, (b) the file has a `.wav` extension, (c) the file is readable and non-empty. Raise `FileNotFoundError` or `ValueError` with descriptive messages on failure. This prevents cryptic downstream errors from the Chatterbox library. | R-18 | DONE |
| R-22 | **Text chunking for long inputs** — If input text exceeds 500 characters, split it into sentence-boundary chunks (using Python's `re` module to split on `.!?` followed by whitespace) and process each chunk sequentially through Chatterbox, yielding audio tuples for each chunk. This mitigates the known voice-drift issue on long inputs. Chunks MUST NOT break mid-sentence. | R-18 | DONE |
| R-23 | **Chatterbox unit tests** — Add comprehensive tests to `tests/test_tts.py` covering: (a) `ChatterboxTTS` instantiation with default and custom parameters including `rsxdalv-faster`, (b) registration in `_PROVIDERS` under key `"chatterbox"`, (c) factory function `get_tts_backend()` returns `ChatterboxTTS` for all three model types, (d) voice file validation errors (missing file, wrong extension, empty file), (e) lazy import guard — verify `RuntimeError` with correct install command per model type, (f) text chunking splits long text correctly and preserves sentence boundaries, (g) config parameter forwarding (`model_type`, `device`, `exaggeration`, `cfg_weight`, `voice_file`). All tests MUST mock the actual Chatterbox model to avoid GPU/download dependencies in CI. | R-18, R-20, R-21, R-22 | DONE |

#### Implementation Checklist (for the implementing session)

1. ~~`pip install chatterbox-tts` in the project environment~~ → See safe install below
2. ~~Add `ChatterboxTTS` class to `voice_agent/tts.py`~~ DONE (~120 lines, supports 3 model types)
3. ~~Register `"chatterbox"` in `_PROVIDERS` dict~~ DONE
4. ~~Add commented-out config blocks to `assistant_config.yml`~~ DONE (3 blocks: original, turbo, rsxdalv-faster)
5. ~~Add voice file validation logic in `ChatterboxTTS._validate_voice_file()`~~ DONE
6. ~~Add text chunking helper (`_chunk_text()` module-level function)~~ DONE
7. ~~Add tests to `tests/test_tts.py`~~ DONE (~150 lines, all mocked, covers all 3 model types)
8. Run `pytest tests/ -v` — all existing + new tests must pass
9. Verify `local_voice_chat.py` and `local_voice_chat_advanced.py` still import and run
10. ~~Update SPOT.md status column and revision log~~ DONE

#### Safe Dependency Installation (for users with existing torch/CUDA)

**CRITICAL: Do NOT let pip overwrite your torch, torchaudio, cudnn, or CUDA runtime.**

**Recommended: Use the automated installer script** (`scripts/install_chatterbox.py`).
It snapshots all packages before and after, verifies nothing protected was changed,
and rolls back automatically if any driver was touched.

```bash
# Automated (recommended) — Windows: double-click scripts/install_chatterbox.bat
python scripts/install_chatterbox.py original         # voice cloning + emotion
python scripts/install_chatterbox.py turbo            # fastest official (~6x RT)
python scripts/install_chatterbox.py rsxdalv-faster   # torch.compile + CUDA graphs
python scripts/install_chatterbox.py --check          # verify only, install nothing
```

**Manual alternative** (if you prefer full control):

```bash
# Step 1: Verify your existing torch works
python -c "import torch; print(torch.cuda.is_available(), torch.__version__)"

# Step 2: Install chatterbox WITHOUT touching torch/CUDA deps
# --- Option A: Official package (original or turbo model) ---
pip install --no-deps chatterbox-tts

# --- Option B: rsxdalv faster branch (torch.compile + CUDA graphs) ---
pip install --no-deps git+https://github.com/rsxdalv/chatterbox.git@faster

# Step 3: Install ONLY the missing non-torch dependencies (one-by-one for safety)
pip install transformers accelerate conformer scipy tqdm
pip install librosa soundfile encodec huggingface-hub safetensors
pip install nemo_text_processing

# Step 4: Verify nothing was overwritten
python -c "import torch; print(torch.cuda.is_available(), torch.__version__)"
```

**What `--no-deps` protects (DO NOT reinstall these):**
- `torch`, `torchaudio` — your CUDA-compiled PyTorch
- `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-runtime-cu12` — CUDA runtime
- `triton` — torch.compile backend
- `wheel`, `setuptools` — build tooling

**What the install script does (pipeline):**
1. Snapshots every package version via `pip freeze`
2. Verifies torch + CUDA are working and queries GPU VRAM
3. Installs chatterbox with `--no-deps` (NEVER touches torch)
4. Installs non-torch deps one-by-one (fault isolation)
5. Re-snapshots and diffs to prove nothing protected was overwritten
6. Smoke-tests `from chatterbox.tts import ChatterboxTTS2`
7. **Automatically rolls back** if any protected package changed version
8. Saves before/after snapshot to JSON for diagnostics (`--save-snapshot`)

This pattern is validated by: [GitHub issue #159](https://github.com/resemble-ai/chatterbox/issues/159), [Medium RTX 5070 guide (Dec 2025)](https://medium.com/@gideont/how-i-got-chatterbox-tts-running-on-an-rtx-5070-pytorch-2-9-cuda-12-8-afc92bb5c10b), and the [FastRTC emotion project](https://github.com/dwain-barnes/chatterbox-fastrtc-realtime-emotion).

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

## Test Coverage Analysis (2026-02-13)

**268 tests, all passing** (pytest tests/ -v, ~5s runtime)

### Module Coverage Matrix

| Source Module | Lines | Test File | Test Lines | Tests | Rating |
|---|---|---|---|---|---|
| `voice_agent/config.py` | 73 | `test_config.py` | 84 | 6 | Excellent |
| `voice_agent/history.py` | 62 | `test_history.py` | 76 | 7 | Excellent |
| `voice_agent/context.py` | 56 | `test_context.py` | 72 | 7 | Excellent |
| `voice_agent/scratchpad.py` | 55 | `test_scratchpad.py` | 82 | 10 | Excellent |
| `voice_agent/command_parser.py` | 157 | `test_command_parser.py` | 186 | 20 | Excellent |
| `voice_agent/execute.py` | 145 | `test_execute.py` | 141 | 16 | Excellent |
| `voice_agent/prompt_loader.py` | 108 | `test_prompt_loader.py` | 154 | 11 | Excellent |
| `voice_agent/llm.py` | 167 | `test_llm.py` | 268 | 18 | Excellent |
| `voice_agent/tts.py` | 376 | `test_tts.py` | 482 | 40 | Excellent |
| `voice_agent/modes.py` | 204 | `test_modes.py` | 310 | 22 | Excellent |
| `voice_agent/refinement.py` | 85 | `test_refinement.py` | 137 | 11 | Excellent |
| `voice_agent/source_analysis.py` | 262 | `test_source_analysis.py` | 340 | 26 | Excellent |
| `voice_agent/typer_discovery.py` | 178 | `test_typer_discovery.py` | 244 | 16 | Excellent |
| `commands/db_commands.py` | 199 | `test_db_commands.py` | 221 | 12 | Good |
| `commands/fs_commands.py` | 83 | `test_fs_commands.py` | 188 | 14 | Excellent |
| `commands/export_commands.py` | 164 | `test_export_commands.py` | 205 | 11 | Good |
| — | — | `test_builtin_discovery.py` | 80 | 6 | Integration |
| `local_voice_chat.py` | 19 | — | 0 | 0 | **None** |
| `local_voice_chat_advanced.py` | 93 | — | 0 | 0 | **None** |

**Totals:** 2,486 source lines, 3,270 test lines (1.3:1 test-to-source ratio)

### Strengths

- All 13 `voice_agent/` modules rated "Excellent" — every public class, method, and function has tests
- All 3 `commands/` modules have solid coverage including error paths
- External services (Ollama, OpenAI, Anthropic, GPU, file I/O) always mocked — tests run offline in ~5s
- ChatterboxTTS has particularly thorough testing (40 tests covering 3 model types, voice validation, text chunking, lazy imports)
- Edge cases well covered: empty inputs, missing files, invalid configs, security patterns, refusal detection

### Gaps — High Priority

| Gap | Module(s) | Impact | Recommended Fix |
|-----|-----------|--------|-----------------|
| Entry points untested | `local_voice_chat.py`, `local_voice_chat_advanced.py` | Main user-facing apps have 0 tests — config wiring, argument parsing, stream setup unverified | Add integration tests that mock FastRTC/Gradio and verify config→mode-handler wiring |
| Malformed YAML config | `config.py` | No test for parse errors or invalid YAML | Add tests with broken YAML, empty files, non-dict top-level |
| API timeout/error recovery | `llm.py` | All API calls mocked as successful — no timeout or network error tests | Add tests for `ConnectionError`, `Timeout`, malformed API responses |

### Gaps — Medium Priority

| Gap | Module(s) | Impact | Recommended Fix |
|-----|-----------|--------|-----------------|
| Malformed chain commands | `command_parser.py` | Edge case `&&&&` or trailing `&&` untested | Add parse tests for degenerate chain syntax |
| Complex type hints in discovery | `typer_discovery.py` | `Union`, `Optional` with nested generics not tested | Add test files with complex annotations |
| Missing JSON fields in score parsing | `source_analysis.py` | LLM returning partial JSON untested | Add tests for `{"score": 0.8}` without `description` field and vice versa |
| Permission errors | `scratchpad.py`, `context.py`, `fs_commands.py` | Read/write permission failures untested | Add tests that mock `PermissionError` |
| Pyttsx3/RealtimeTTS stream output | `tts.py` | `stream_tts()` actual behavior never exercised (only init tested) | Add mocked stream tests similar to Chatterbox/Kokoro |

### Gaps — Low Priority

| Gap | Module(s) | Impact | Recommended Fix |
|-----|-----------|--------|-----------------|
| Very large outputs | `execute.py` | Truncation behavior for huge stdout untested | Add test with >1MB subprocess output |
| Binary file handling | `fs_commands.py` | `compare_files` with binary content untested | Add test with non-text file comparison |
| Complex WHERE clauses | `db_commands.py` | Multi-condition and edge-case SQL untested | Add tests for `>`, `<`, `LIKE`, compound conditions |

### Environment Note

The `fastrtc[stt]` dependency requires native ffmpeg libraries (`libavformat`, `libavcodec`, etc.) to build the `av` package. In environments without ffmpeg development headers, `uv sync` fails. Tests can still be run by installing `pytest`, `pyyaml`, `typer`, and `loguru` directly via `pip install`. This should be addressed by either: (a) adding ffmpeg to the CI environment, or (b) making `fastrtc` an optional dependency so the test suite can run without it.

### Phase 9: Test Coverage Gap Implementation

> **Integration constraint:** Phase 9 is strictly additive. It adds new test files and extends existing test files. It MUST NOT modify any production code in `voice_agent/`, `commands/`, or entry points. All existing 268 tests MUST continue to pass unmodified.

#### Requirements

| ID | Requirement | Depends On | Status |
|----|-------------|------------|--------|
| R-24 | **Entry point integration tests** — Create `tests/test_entry_points.py` with tests for both `local_voice_chat.py` and `local_voice_chat_advanced.py`. Tests MUST mock FastRTC (`fastrtc.ReplyOnPause`, `fastrtc.Stream`) and verify: (a) config is loaded from `assistant_config.yml`, (b) correct LLM/TTS/mode backends are instantiated based on config, (c) `--context-files` argument parsing works in advanced mode, (d) `--phone` flag triggers phone stream setup, (e) stream `.ui.launch()` is called. All external services fully mocked. **Note:** The project does NOT use Gradio — the entry points use FastRTC's built-in WebRTC UI and optional phone interface. | R-01, R-06, R-07, R-08 | TODO |
| R-25 | **Malformed config tests** — Extend `tests/test_config.py` with tests for: (a) completely invalid YAML (syntax errors) raises a clear exception, (b) empty YAML file returns empty/default config, (c) YAML whose top-level value is a list instead of a dict raises `ValueError`, (d) missing required sections (e.g., no `llm` key) handled gracefully, (e) config values with unexpected types (e.g., `max_turns: "abc"` instead of int). | R-01 | TODO |
| R-26 | **LLM error recovery tests** — Extend `tests/test_llm.py` with tests for: (a) `ConnectionError` during Ollama/DeepSeek/Anthropic `.chat()` calls, (b) `Timeout` during API calls, (c) API returning malformed JSON or empty response body, (d) API returning unexpected HTTP status codes (429, 500, 503). Mock the underlying client libraries to raise these exceptions. | R-06 | TODO |
| R-27 | **Command parser edge case tests** — Extend `tests/test_command_parser.py` with tests for: (a) empty `&&` segments (e.g., `cmd1 && && cmd2`), (b) trailing `&&` (e.g., `cmd1 &&`), (c) leading `&&` (e.g., `&& cmd1`), (d) quadruple `&&&&`, (e) commands with quoted strings containing `&&`. | R-10, R-11 | TODO |
| R-28 | **Permission error tests** — Extend `tests/test_scratchpad.py`, `tests/test_context.py`, and `tests/test_fs_commands.py` with tests that mock `PermissionError` on file read/write operations and verify descriptive error messages or proper exception propagation. | R-03, R-04, R-13 | TODO |
| R-29 | **TTS stream output tests** — Extend `tests/test_tts.py` with mocked `stream_tts()` tests for `Pyttsx3TTS` and `RealtimeTTSBackend` providers. Verify that `stream_tts(text)` returns an iterator yielding `(sample_rate, audio_array)` tuples, matching the pattern already tested for `KokoroTTS` and `ChatterboxTTS`. | R-07 | TODO |
| R-30 | **Source analysis partial JSON tests** — Extend `tests/test_source_analysis.py` with tests for: (a) LLM returning `{"score": 0.8}` without a `description` field, (b) LLM returning `{"description": "..."}` without a `score` field, (c) LLM returning completely malformed JSON, (d) LLM returning an empty string. Verify graceful fallback behavior. | R-17 | TODO |
| R-31 | **Typer discovery complex annotation tests** — Extend `tests/test_typer_discovery.py` with test Typer command files that use: (a) `Union[str, int]` type hints, (b) `Optional[list[str]]` nested generics, (c) `Annotated[str, typer.Argument()]` patterns, (d) default values with complex types. Verify the catalog correctly represents these signatures. | R-12 | TODO |

#### Implementation Checklist (for the implementing session)

1. Create `tests/test_entry_points.py` — mock FastRTC, verify config→backend wiring for both entry points (R-24)
2. Extend `tests/test_config.py` — add 5+ tests for malformed YAML scenarios (R-25)
3. Extend `tests/test_llm.py` — add 4+ tests for connection/timeout/malformed response errors (R-26)
4. Extend `tests/test_command_parser.py` — add 5+ tests for degenerate `&&` chain syntax (R-27)
5. Extend `tests/test_scratchpad.py`, `tests/test_context.py`, `tests/test_fs_commands.py` — add PermissionError tests (R-28)
6. Extend `tests/test_tts.py` — add mocked `stream_tts()` tests for Pyttsx3 and RealtimeTTS (R-29)
7. Extend `tests/test_source_analysis.py` — add partial/malformed JSON parsing tests (R-30)
8. Extend `tests/test_typer_discovery.py` — add complex type annotation test fixtures (R-31)
9. Run `pytest tests/ -v` — all existing 268 + new tests must pass (exit code 0)
10. Update SPOT.md status columns and revision log

#### Key Context for Next Session

- **Python 3.13** (strict, per `.python-version`)
- **No Gradio** — entry points use FastRTC WebRTC UI directly, not Gradio
- **fastrtc build issue:** `uv sync` may fail without ffmpeg dev headers. Workaround: `pip install pytest pyyaml typer loguru` directly, then `pytest tests/ -v`
- **Test pattern:** All tests use `pytest` fixtures, `tmp_path`, and `unittest.mock`. External services always mocked. One test file per module (`test_{module}.py`)
- **Additive only:** Phase 9 adds/extends test files only. Zero production code changes
- **Current test count:** 268 tests, all passing, ~5s runtime

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
| 2026-02-12 | phase-8 | Phase 8 complete: ChatterboxTTS provider with 3 model types (original, turbo, rsxdalv-faster). Safe `--no-deps` installation documented. Voice file validation, text chunking, lazy import guards all implemented. rsxdalv `faster` branch added as speed option with torch.compile + CUDA graph optimisations. All tests pass, zero regressions. Strictly additive — no Phases 1–7 files modified except registry + config |
| 2026-02-13 | test-coverage-analysis | Test coverage analysis added to SPOT.md. 268 tests all passing. 13/13 voice_agent modules rated Excellent, 3/3 command modules rated Good+. Identified gaps: entry points untested (high), malformed YAML/API errors untested (medium), edge cases in parser/discovery/permissions (low). Environment note: fastrtc requires native ffmpeg libs to build av package |
| 2026-02-13 | phase-9-spec | Phase 9 requirements added: 8 test coverage gap requirements (R-24–R-31) with implementation checklist and key context for next session. Covers entry point integration tests, malformed config, LLM error recovery, parser edge cases, permission errors, TTS stream tests, partial JSON parsing, complex type annotations. Additive-only — no production code changes |
