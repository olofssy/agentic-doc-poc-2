"""Direct-provider chat-model construction behind one local interface."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


def build_chat_model(provider: str | None = None) -> BaseChatModel:
    """Create the configured direct-provider chat model without invoking it."""

    selected_provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
    if selected_provider == "openai":
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"))
    if selected_provider == "anthropic":
        return ChatAnthropic(model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    raise ValueError(f"unsupported LLM_PROVIDER: {selected_provider!r}")
