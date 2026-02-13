# CLAUDE.md — AI Assistant Guide for Local Voice AI Agent

## Project Overview

A fully local, privacy-first voice AI assistant that listens, understands, remembers, and acts on your behalf through natural speech. It supports swappable AI backends (LLM, TTS, STT) and can run with zero cloud dependency. Users interact via WebRTC browser UI or a temporary phone number.

## Tech Stack

- **Language:** Python 3.13 (strict — specified in `.python-version`)
- **Package manager:** `uv` (lock file: `uv.lock`)
- **Core dependencies:** FastRTC (WebRTC + Moonshine STT + Kokoro TTS), Ollama (local LLM), PyYAML, Typer, Loguru
- **Optional backends:** DeepSeek (via `openai`), Anthropic Claude, pyttsx3, RealtimeTTS, Chatterbox TTS (voice cloning)
- **Testing:** pytest (>=8.0)

## Repository Structure

```
├── voice_agent/              # Core application package
│   ├── config.py             # YAML config loader with dot-path access (ConfigNode)
│   ├── llm.py                # LLM abstraction — OllamaLLM, DeepSeekLLM, AnthropicLLM
│   ├── tts.py                # TTS abstraction — KokoroTTS, Pyttsx3TTS, RealtimeTTSBackend, ChatterboxTTS
│   ├── modes.py              # Mode architecture — ChatMode, AgentMode handlers
│   ├── history.py            # Conversation history (list of {role, content} messages)
│   ├── scratchpad.py         # Persistent cross-session memory (scratchpad.md)
│   ├── context.py            # Context file injection into prompts
│   ├── prompt_loader.py      # XML prompt template loading and variable interpolation
│   ├── command_parser.py     # LLM output → CLI command parsing and validation
│   ├── execute.py            # Subprocess execution with timeout
│   ├── refinement.py         # Optional LLM response refinement for spoken delivery
│   ├── source_analysis.py    # Documentation source relevance scoring and ranking
│   └── typer_discovery.py    # Typer command file discovery and catalog generation
├── commands/                 # Built-in Typer command files (auto-discovered)
│   ├── db_commands.py        # SQLite CRUD operations
│   ├── export_commands.py    # JSON/YAML/CSV export
│   └── fs_commands.py        # File system operations (list, diff, backup, restore)
├── prompts/                  # XML prompt templates
│   ├── system_prompt.xml     # Chat mode system prompt
│   ├── agent_command_prompt.xml  # Agent mode system prompt
│   ├── refinement_prompt.xml
│   ├── source_relevance_prompt.xml
│   └── source_summary_prompt.xml
├── tests/                    # pytest test suite (mirrors voice_agent/ + commands/)
├── scripts/                  # Utility scripts (Chatterbox installer with rollback)
├── local_voice_chat.py       # Simple entry point (direct FastRTC voice I/O)
├── local_voice_chat_advanced.py  # Advanced entry point (modes, context files, phone)
├── assistant_config.yml      # Single YAML config for all settings
├── pyproject.toml            # Project metadata, dependencies, pytest config
├── SPOT.md                   # Design spec — 8 phases, 23 requirements, revision log
└── uv.lock                   # Dependency lock file
```

## Common Commands

```bash
# Setup
uv venv && source .venv/bin/activate && uv sync
ollama pull gemma3:4b

# Run tests (all tests)
pytest tests/ -v

# Run a specific test file
pytest tests/test_llm.py -v

# Run the application
python local_voice_chat.py                          # Simple mode
python local_voice_chat_advanced.py                 # Advanced mode (Gradio UI)
python local_voice_chat_advanced.py --phone          # Phone number interface
python local_voice_chat_advanced.py --context-files doc1.txt doc2.txt

# Install optional dependencies
uv sync --extra deepseek      # DeepSeek LLM backend
uv sync --extra anthropic     # Anthropic Claude backend
uv sync --extra pyttsx3       # pyttsx3 TTS backend
uv sync --extra dev           # pytest (development)
```

## Architecture Patterns

### Provider/Registry Pattern
All swappable backends (LLM, TTS, modes) follow the same pattern:
1. Abstract base class with a defined interface (`LLMBackend`, `TTSBackend`, `ModeHandler`)
2. Concrete implementations as subclasses
3. A `_PROVIDERS` / `_MODES` dict registry mapping string keys to classes
4. A `get_*_backend(config)` factory function that reads `assistant_config.yml` and instantiates the correct provider

### Lazy Imports
Heavy dependencies (ollama, openai, anthropic, fastrtc, pyttsx3, chatterbox, torch, numpy) are imported inside methods, not at module level. This keeps startup fast and allows the app to work without optional packages installed.

### Configuration
All settings flow through `assistant_config.yml` → `ConfigNode` (dot-path access). The `ConfigNode` wraps a dict and creates nested `ConfigNode` objects for sub-dicts. Access config via `config.section.key` or `config.get("key", default)`.

### Prompt Templates
XML files in `prompts/` with `{variable}` placeholders. Loaded by `prompt_loader.render_template(name, variables={...})`. Template names correspond to filenames without extension.

### Mode Architecture
Two modes — `chat` (conversational) and `agent` (CLI command execution). Both share the same LLM/TTS/STT backends and conversation history. Mode is set in config. Each mode builds its own system prompt from a different XML template.

### Additive Phase Design
Features are organized into 8 phases (see `SPOT.md`). Later phases are strictly additive — they do not modify earlier phase code. Optional features (refinement, source analysis) are gated by boolean config flags.

## Code Conventions

- **Docstrings:** Every module and class has a docstring. Module docstrings reference the SPOT requirement ID (e.g., `(R-06)`).
- **Type hints:** All function signatures use type hints. `from __future__ import annotations` is used in all modules for forward references.
- **Imports:** `from __future__ import annotations` at top. Standard library, then third-party, then local imports. Heavy deps are lazy-imported inside methods.
- **Naming:** snake_case for functions/variables, PascalCase for classes. Provider classes are named `{Name}{Type}` (e.g., `OllamaLLM`, `KokoroTTS`, `ChatMode`).
- **Error handling:** Descriptive error messages with context. `RuntimeError` for missing optional dependencies. `ValueError` for invalid config. `FileNotFoundError` for missing files.
- **Tests:** One test file per module (`test_{module}.py`). Tests use `pytest` fixtures, `tmp_path`, and mocking (`unittest.mock`). External services (Ollama, APIs, GPU) are always mocked.
- **No CI/CD pipeline** currently configured.

## Testing Guidelines

- All tests are in `tests/` and discovered via `pytest` using `testpaths = ["tests"]` in `pyproject.toml`.
- Tests must not require network access, GPUs, or running services — mock all external dependencies.
- Test files follow the naming convention `test_{module_name}.py`.
- Every new feature must have corresponding tests. All existing tests must continue to pass (zero regressions).
- Run `pytest tests/ -v` before committing. The quality gateway requires exit code 0.

## Configuration Reference

The single config file `assistant_config.yml` controls:

| Section | Key Fields | Purpose |
|---------|-----------|---------|
| `assistant` | `name`, `persona` | Assistant identity and system persona |
| `human` | `name` | User's display name |
| `stt` | `engine` | Speech-to-text engine (default: `moonshine`) |
| `llm` | `provider`, `model` | LLM backend selection (`ollama`, `deepseek`, `anthropic`) |
| `tts` | `provider`, `voice` | TTS backend selection (`kokoro`, `pyttsx3`, `realtimetts`, `chatterbox`) |
| `mode` | — | Operating mode (`chat` or `agent`) |
| `conversation` | `max_turns` | Max conversation history length |
| `scratchpad` | `file` | Persistent memory file path |
| `execution` | `timeout` | Subprocess execution timeout in seconds |
| `refinement` | `enabled` | Toggle LLM response refinement for spoken delivery |
| `source_analysis` | `enabled`, `relevance_threshold` | Toggle documentation source scoring/filtering |

## Key Design Decisions

- **Privacy-first:** Default configuration runs entirely locally (Ollama + Moonshine + Kokoro). No API keys needed.
- **Single config file:** All backend, persona, and feature settings live in one YAML file (`assistant_config.yml`).
- **Extensible commands:** New voice commands are added by dropping a `*_commands.py` Typer file into `commands/`. The system auto-discovers and catalogs them.
- **Chatterbox TTS isolation:** Installed with `--no-deps` to avoid overwriting existing torch/CUDA. Lazy-imported so it has zero impact if not installed. A dedicated installer script (`scripts/install_chatterbox.py`) handles safe installation with rollback.

## SPOT.md

The `SPOT.md` file is the Single Point of Truth design document. It contains:
- The project's north star and end-user outcomes
- 13 success factors
- 23 requirements across 8 phases with status tracking
- Quality gateway checklist
- A revision log of all changes

Update `SPOT.md` status columns and revision log when completing requirements.
