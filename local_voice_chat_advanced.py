import sys
import argparse

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger
from ollama import chat

from voice_agent.config import load_config
from voice_agent.history import ConversationHistory
from voice_agent.scratchpad import scratchpad_prompt_section

stt_model = get_stt_model()  # moonshine/base
tts_model = get_tts_model()  # kokoro

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Load configuration (R-01)
config = load_config()

# Build system prompt with optional scratchpad injection (R-03)
base_persona = config.assistant.persona
scratchpad_section = scratchpad_prompt_section(config.scratchpad.file)
system_prompt = base_persona + scratchpad_section

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
    args = parser.parse_args()

    logger.info(f"Assistant: {config.assistant.name} | LLM: {config.llm.provider}/{config.llm.model} | Mode: {config.mode}")
    stream = create_stream()

    if args.phone:
        logger.info("Launching with FastRTC phone interface...")
        stream.fastphone()
    else:
        logger.info("Launching with Gradio UI...")
        stream.ui.launch()
