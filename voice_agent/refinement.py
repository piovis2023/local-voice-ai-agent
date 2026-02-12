"""LLM response refinement pipeline (R-16).

Optional post-processing that takes any response (LLM reply or CLI output)
and refines it for succinct, natural, spoken audio delivery via TTS.

Enable/disable via ``refinement.enabled`` in ``assistant_config.yml``.
When disabled, behaviour is identical to the existing pipeline.
"""

from __future__ import annotations

from voice_agent.config import ConfigNode
from voice_agent.llm import LLMBackend
from voice_agent.prompt_loader import render_template


def is_refinement_enabled(config: ConfigNode) -> bool:
    """Check whether the refinement pipeline is enabled in the config.

    Returns ``True`` only when ``config.refinement.enabled`` is explicitly
    set to ``True``.  Defaults to ``False`` (disabled).
    """
    refinement = config.get("refinement")
    if refinement is None:
        return False
    if isinstance(refinement, dict):
        return bool(refinement.get("enabled", False))
    # ConfigNode
    return bool(getattr(refinement, "enabled", False))


def refine_response(
    response: str,
    llm: LLMBackend,
    config: ConfigNode | None = None,
) -> str:
    """Refine a raw response for spoken audio delivery.

    Passes *response* through the LLM with the ``refinement_prompt`` XML
    template to produce output that is succinct, includes natural filler
    words, and is factually accurate to the source.

    Parameters
    ----------
    response:
        The raw response text to refine (LLM reply or CLI output).
    llm:
        The LLM backend to use for the refinement pass.
    config:
        Optional config; if provided and refinement is disabled, returns
        *response* unchanged.

    Returns
    -------
    str
        The refined response text, or the original *response* if refinement
        is disabled or the input is empty.
    """
    if config is not None and not is_refinement_enabled(config):
        return response

    if not response or not response.strip():
        return response

    try:
        prompt_text = render_template(
            "refinement_prompt",
            variables={"source_response": response},
        )
    except FileNotFoundError:
        # Template missing — fall back to a minimal inline prompt.
        prompt_text = (
            "Rewrite the following response for spoken audio delivery. "
            "Be succinct, use natural filler words, stay factually accurate, "
            "and use a matter-of-fact tone. Do not add information that is "
            "not in the original.\n\n"
            f"Source response:\n{response}"
        )

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": "Refine the source response above for audio delivery."},
    ]

    return llm.chat(messages)
