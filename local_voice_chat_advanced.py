import sys
import argparse

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger
from ollama import chat

from voice_agent.config import load_config
from voice_agent.context import context_prompt_section
from voice_agent.history import ConversationHistory
from voice_agent.prompt_loader import render_template
from voice_agent.scratchpad import scratchpad_prompt_section

stt_model = get_stt_model()  # moonshine/base
tts_model = get_tts_model()  # kokoro

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Load configuration (R-01)
config = load_config()


def build_system_prompt(context_files: list[str] | None = None) -> str:
    """Assemble the full system prompt using XML template with variable interpolation (R-05).

    Falls back to simple string concatenation if the template is unavailable.
    """
    scratchpad_section = scratchpad_prompt_section(config.scratchpad.file)
    context_section = context_prompt_section(context_files or [])

    try:
        return render_template(
            "system_prompt",
            variables={
                "assistant_name": config.assistant.name,
                "persona": config.assistant.persona,
                "scratchpad": scratchpad_section,
                "context": context_section,
            },
        )
    except FileNotFoundError:
        # Fallback: concatenate directly (backwards-compatible)
        return config.assistant.persona + scratchpad_section + context_section


# Default system prompt (no context files) for module-level import compatibility
system_prompt = build_system_prompt()

# Session conversation history (R-02)
history = ConversationHistory(max_turns=config.conversation.max_turns)
history.add("system", system_prompt)


def echo(audio):
    transcript = stt_model.stt(audio)
    logger.debug(f"Transcript: {transcript}")

    # Add user message to history (R-02)
    history.add("user", transcript)

    response = chat(
        model=config.llm.model,
        messages=history.get_messages_for_llm(),
        options={"num_predict": 200},
    )
    response_text = response["message"]["content"]
    logger.debug(f"Response: {response_text}")

    # Add assistant response to history (R-02)
    history.add("assistant", response_text)

    for audio_chunk in tts_model.stream_tts_sync(response_text):
        yield audio_chunk


def create_stream():
    return Stream(ReplyOnPause(echo), modality="audio", mode="send-receive")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Voice Chat Advanced")
    parser.add_argument(
        "--phone",
        action="store_true",
        help="Launch with FastRTC phone interface (get a temp phone number)",
    )
    parser.add_argument(
        "--context-files",
        nargs="+",
        default=[],
        metavar="FILE",
        help="One or more file paths to inject as reference material into the system prompt (R-04)",
    )
    args = parser.parse_args()

    # Rebuild system prompt with context files if provided (R-04)
    if args.context_files:
        system_prompt = build_system_prompt(args.context_files)
        history.clear()
        history.add("system", system_prompt)

    logger.info(f"Assistant: {config.assistant.name} | LLM: {config.llm.provider}/{config.llm.model} | Mode: {config.mode}")
    if args.context_files:
        logger.info(f"Context files loaded: {args.context_files}")
    stream = create_stream()

    if args.phone:
        logger.info("Launching with FastRTC phone interface...")
        stream.fastphone()
    else:
        logger.info("Launching with Gradio UI...")
        stream.ui.launch()
