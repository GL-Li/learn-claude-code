#!/usr/bin/env python3
# Harness: the loop -- the model's first connection to the real world.
"""
s01_agent_loop.py - The Agent Loop

The entire secret of an AI coding agent in one pattern:

    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.
"""

import os
import subprocess
import uuid

from langchain_ollama import ChatOllama
from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.25:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest")

llm = ChatOllama(
    model=MODEL,
    base_url=OLLAMA_BASE_URL,
)

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run"}
            },
            "required": ["command"]
        }
    }
}]


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


# -- The core pattern: a while loop that calls tools until the model stops --
def agent_loop(messages: list):
    # Prepend system prompt if this is the first message
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": SYSTEM})
    
    while True:
        response = llm.invoke(
            messages,
            tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content or ""})
        if not response.tool_calls:
            return
        for tool_call in response.tool_calls:
            command = tool_call["args"].get("command", "")
            print(f"\033[33m$ {command}\033[0m")
            output = run_bash(command)
            print(output[:200])
            # Use tool role with the generated ID
            messages.append({
                "role": "tool",
                "tool_call_id": str(uuid.uuid4()),
                "content": output
            })


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        # Find the last assistant message in history
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break
        print()
