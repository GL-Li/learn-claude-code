#!/usr/bin/env python3
# Harness: on-demand knowledge -- domain expertise, loaded when the model asks.
"""
s05_skill_langgraph.py - Skills with LangGraph

Two-layer skill injection that avoids bloating the system prompt:

    Layer 1 (cheap): skill names in system prompt (~100 tokens/skill)
    Layer 2 (on demand): full skill body in tool_result

    skills/
      pdf/
        SKILL.md          <-- frontmatter (name, description) + body
      code-review/
        SKILL.md

    System prompt:
    +--------------------------------------+
    | You are a coding agent.              |
    | Skills available:                    |
    |   - pdf: Process PDF files...        |  <-- Layer 1: metadata only
    |   - code-review: Review code...      |
    +--------------------------------------+

    When model calls load_skill("pdf"):
    +--------------------------------------+
    | tool_result:                         |
    | <skill>                              |
    |   Full PDF processing instructions   |  <-- Layer 2: full body
    |   Step 1: ...                        |
    |   Step 2: ...                        |
    | </skill>                             |
    +--------------------------------------+

Key insight: "Don't put everything in the system prompt. Load on demand."

LangGraph implementation features:
1. Pydantic State definition
2. LangChain @tool decorator for tools
3. LangGraph StateGraph with conditional routing
4. Idiomatic LangGraph patterns

Sample Questions to Demonstrate Usage:

1. "What skills are available to help me with PDF processing?"
   - Demonstrates: Layer 1 skill metadata in system prompt
   - The agent will list available skills from the system prompt
   - Shows how skill descriptions are injected without loading full content

2. "load_skill pdf"
   - Demonstrates: Layer 2 on-demand skill loading via tool call
   - The agent will call the load_skill tool with "pdf" argument
   - Returns full PDF processing instructions wrapped in <skill> tags
   - Shows the two-layer architecture: metadata first, full content on demand

Additional examples:
- "How can I extract text from a PDF file?" (triggers load_skill pdf)
- "I need to review some Python code" (triggers load_skill code-review)
- "bash ls -la" (tests tool execution in LangGraph workflow)
"""

import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional
from typing_extensions import Literal

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.25:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:q8_0")
WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"

# ============================================================================
# Pydantic State Definition
# ============================================================================

class AgentState(BaseModel):
    """State for the LangGraph agent using Pydantic BaseModel."""
    messages: List[BaseMessage] = Field(default_factory=list, description="The conversation history")
    skill_content: Optional[str] = Field(default=None, description="Loaded skill content")
    last_tool_outputs: List[str] = Field(default_factory=list, description="Tool outputs from last step")

# ============================================================================
# SkillLoader (unchanged from original)
# ============================================================================

class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        """Parse YAML frontmatter between --- delimiters."""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        meta = {}
        for line in match.group(1).strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """Layer 1: short descriptions for the system prompt."""
        if not self.skills:
            return "(no skills available)"
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "No description")
            tags = skill["meta"].get("tags", "")
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: full skill body returned in tool_result."""
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"

# ============================================================================
# LangChain Tools with @tool decorator
# ============================================================================

SKILL_LOADER = SkillLoader(SKILLS_DIR)

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
def read_file(path: str, limit: Optional[int] = None) -> str:
    """Read file contents."""
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
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
        return f"Wrote {len(content)} bytes"
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

@tool
def load_skill(name: str) -> str:
    """Load specialized knowledge by name."""
    return SKILL_LOADER.get_content(name)

# ============================================================================
# LangGraph Setup
# ============================================================================

# Create tools list
tools = [bash, read_file, write_file, edit_file, load_skill]

# Create LLM with tools
llm = ChatOllama(model=MODEL, base_url=OLLAMA_BASE_URL)
llm_with_tools = llm.bind_tools(tools)

# Layer 1: skill metadata injected into system prompt
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

Skills available:
{SKILL_LOADER.get_descriptions()}"""

def call_model(state: AgentState) -> dict:
    """Call the LLM with the current state."""
    messages = state.messages
    
    # Add system message if not present
    if not messages or not isinstance(messages[0], BaseMessage) or messages[0].type != "system":
        messages = [SystemMessage(content=SYSTEM)] + messages
    
    # Call LLM
    response = llm_with_tools.invoke(messages)
    
    # Return only fields that need updating (LangGraph pattern)
    return {
        "messages": messages + [response],
        "last_tool_outputs": []  # Clear tool outputs
    }

def execute_tools(state: AgentState) -> dict:
    """Execute tools requested by the LLM."""
    messages = state.messages
    last_message = messages[-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}
    
    # Execute each tool
    tool_messages = []
    tool_outputs = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Find and execute the tool
        output = None
        for tool in tools:
            if tool.name == tool_name:
                try:
                    output = tool.invoke(tool_args)
                except Exception as e:
                    output = f"Error: {e}"
                break
        
        if output is None:
            output = f"Error: Unknown tool '{tool_name}'"
        
        # Create ToolMessage
        tool_messages.append(
            ToolMessage(content=str(output), tool_call_id=tool_call["id"])
        )
        tool_outputs.append(str(output))
        
        # Print tool execution for visibility
        print(f"> {tool_name}: {str(output)[:200]}")
    
    # Return only fields that need updating (LangGraph pattern)
    return {
        "messages": messages + tool_messages,
        "last_tool_outputs": tool_outputs
    }

def should_continue(state: AgentState) -> Literal["tools", END]:
    """Determine whether to continue to tools or end."""
    messages = state.messages
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# ============================================================================
# Build the Graph
# ============================================================================

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

# Set entry point
workflow.set_entry_point("agent")

# Add conditional edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# Add edge from tools back to agent
workflow.add_edge("tools", "agent")

# Compile the graph
app = workflow.compile()

# ============================================================================
# Main Execution
# ============================================================================

def run_agent_loop():
    """Run the agent loop with LangGraph."""
    print(f"\033[36ms05_langgraph >> \033[0m", end="")
    
    # Initialize state as AgentState
    initial_state = AgentState(
        messages=[],
        skill_content=None,
        last_tool_outputs=[]
    )
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    while True:
        try:
            query = input()
        except (EOFError, KeyboardInterrupt):
            break
            
        if query.strip().lower() in ("q", "exit", ""):
            break
        
        # Add user message
        initial_state.messages.append(HumanMessage(content=query))
        
        # Run the graph - returns updated state dict
        final_state_dict = app.invoke(initial_state, config)
        
        # Update state for next iteration (merge with current state)
        # Convert dict updates back to AgentState
        updated_state = initial_state.model_copy(update=final_state_dict)
        initial_state = updated_state
        
        # Print assistant's last response
        messages = initial_state.messages
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                print(f"\033[33m{msg.content}\033[0m")
                break
        
        print(f"\033[36ms05_langgraph >> \033[0m", end="")

if __name__ == "__main__":
    run_agent_loop()
