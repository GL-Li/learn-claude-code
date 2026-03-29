# Agent Development Guide

This document describes the development environment and patterns for AI agents in this project.

## Package Management

This project uses **uv** for Python package management.

## LLM model
Use local Ollama model for test. When asked to use Ollama model, use this one:

```python
from langchain_ollama import ChatOllama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.25:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:q8_0")
llm = ChatOllama(model=MODEL, base_url=OLLAMA_BASE_URL)
```


### Running Python Scripts

Use `uv run` to execute Python agent scripts:

```bash
uv run python agents/s01_agent_loop.py
uv run python agents/s02_tool_use.py
uv run python agents/s03_todo_write.py
```

### Adding Dependencies

Add new dependencies with:

```bash
uv add <package-name>
```

### Locking Dependencies

Update the lock file when dependencies change:

```bash
uv lock
```

### Virtual Environment

uv automatically creates and manages the virtual environment. No need to manually activate it when using `uv run`.
