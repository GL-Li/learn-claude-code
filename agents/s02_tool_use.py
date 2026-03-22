#!/usr/bin/env python3
# Harness: tool dispatch -- expanding what the model can reach.
"""
s02_tool_use.py - Tools

The agent loop from s01 didn't change. We just added tools to the array
and a dispatch map to route calls.

    +----------+      +-------+      +------------------+
    |   User   | ---> |  LLM  | ---> | Tool Dispatch    |
    |  prompt  |      |       |      | {                |
    +----------+      +---+---+      |   bash: run_bash |
                          ^          |   read: run_read |
                          |          |   write: run_wr  |
                          +----------+   edit: run_edit |
                          tool_result| }                |
                                     +------------------+

Key insight: "The loop didn't change at all. I just added tools."
"""

import os
import subprocess
import uuid
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain.messages import ToolMessage
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.25:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:q8_0")
llm = ChatOllama(model=MODEL, base_url=OLLAMA_BASE_URL)

WORKDIR = Path.cwd()

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


@tool
def bash(command: str) -> str:
    """Run a shell command."""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents."""
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to file."""
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in file."""
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOLS = [bash, read_file, write_file, edit_file]
TOOL_MAP = {t.name: t for t in TOOLS}


def agent_loop(messages: list):
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": SYSTEM})
    
    while True:
        response = llm.bind_tools(TOOLS).invoke(messages)
        messages.append({"role": "assistant", "content": response.content or ""})
        
        if not response.tool_calls:
            return
        
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            
            if name == "bash":
                print(f"\033[33m$ {args['command']}\033[0m")
            else:
                print(f"> {name}")
            
            tool_output = TOOL_MAP[name].invoke(args)
            messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break
        print()
