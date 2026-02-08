"""LLM adapters."""

from ...config import LLMConfig, LLMProvider
from ...ports.llm import LLMPort
from .claude_api import ClaudeAPIAdapter
from .claude_cli import ClaudeCLIAdapter
from .ollama import OllamaAdapter

__all__ = ["ClaudeCLIAdapter", "ClaudeAPIAdapter", "OllamaAdapter", "create_llm_adapter"]


def create_llm_adapter(config: LLMConfig) -> LLMPort:
    """Create LLM adapter based on configuration."""
    if config.provider == LLMProvider.OLLAMA:
        return OllamaAdapter(model=config.model, base_url=config.ollama_url)
    elif config.provider == LLMProvider.CLAUDE_CLI:
        return ClaudeCLIAdapter()
    elif config.provider == LLMProvider.CLAUDE_API:
        return ClaudeAPIAdapter(model=config.model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")
