import sys
import argparse

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger

from voice_agent.config import load_config
from voice_agent.llm import get_llm_backend
from voice_agent.modes import get_mode_handler

stt_model = get_stt_model()  # moonshine/base
tts_model = get_tts_model()  # kokoro

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Load configuration (R-01)
config = load_config()

# Create shared LLM backend (R-06) and mode handler (R-08)
llm = get_llm_backend(config)
mode_handler = get_mode_handler(config, llm=llm)


def echo(audio):
    transcript = stt_model.stt(audio)
    logger.debug(f"Transcript: {transcript}")

    # Delegate to the active mode handler (R-08)
    response_text = mode_handler.handle_turn(transcript)
    logger.debug(f"Response: {response_text}")

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

    # Rebuild mode handler with context files if provided (R-04, R-08)
    if args.context_files:
        mode_handler = get_mode_handler(
            config, llm=llm, context_files=args.context_files,
        )

    logger.info(
        f"Assistant: {config.assistant.name} | "
        f"LLM: {config.llm.provider}/{config.llm.model} | "
        f"Mode: {mode_handler.mode_name}"
    )
    if args.context_files:
        logger.info(f"Context files loaded: {args.context_files}")
    stream = create_stream()

    if args.phone:
        logger.info("Launching with FastRTC phone interface...")
        stream.fastphone()
    else:
        logger.info("Launching with Gradio UI...")
        stream.ui.launch()
