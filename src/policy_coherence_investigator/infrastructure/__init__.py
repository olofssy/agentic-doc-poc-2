"""Provider configuration kept outside deterministic investigation code."""

from .llm import build_chat_model

__all__ = ["build_chat_model"]
