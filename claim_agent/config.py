"""
LLM backend configuration. Swap providers by changing LLM_PROVIDER in your .env file.

Supported:
  - anthropic  (recommended: best tool-calling reliability for ReAct agents)
  - openai
  - ollama     (free, fully local, no API key — requires Ollama installed)
"""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()


def get_chat_client():
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            temperature=0,
        )

    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0,
        )

    elif LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            temperature=0,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'anthropic', 'openai', or 'ollama'."
        )
