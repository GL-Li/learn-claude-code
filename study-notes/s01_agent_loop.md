# Study Notes: s01_agent_loop.py

## Core Concepts

### Agent Loop Pattern
The agent loop is the fundamental pattern for AI coding agents:
- While `stop_reason == "tool_use"`: call LLM → execute tools → append results
- The loop continues until the model decides to stop (no more tool calls)

### Tools Definition
Tools define the function signatures the LLM can call using OpenAI-compatible JSON format:
- `type`: "function" indicates this is a tool
- `function.name`: The tool name the model uses
- `function.description`: Prompt instruction for when to use the tool
- `function.parameters`: JSON Schema defining required arguments

### subprocess Module
- Executes commands in a **separate process** (parallel from Python's perspective)
- `subprocess.run()` is **synchronous**—waits for completion
- Key parameters:
  - `shell=True`: Execute through shell (allows pipes, redirection)
  - `capture_output=True`: Capture stdout/stderr
  - `text=True`: Return strings instead of bytes
  - `timeout=120`:Wall time limit (real-world elapsed time)
  - `cwd=os.getcwd()`: Set working directory

### Security Considerations
- Block dangerous commands: `rm -rf /`, `sudo`, `shutdown`, `reboot`, `> /dev/`
- `> /dev/` check prevents output redirection attacks (e.g., `> /etc/passwd`)
- Use list form `["python", "script.py"]` for safety to prevent argument injection
- `shell=True` requires command blocking since user input can contain malicious commands

### Process Parallelism
- subprocess creates isolated processes with their own memory space
- Can utilize multiple CPU cores
- `subprocess.run()`: blocking (waits for completion)
- `subprocess.Popen()`: non-blocking (for parallel execution)

### Color-Coded Output
ANSI escape codes for terminal visualization:
- `\033[33m`: Yellow (commands)
- `\033[36m`: Cyan (user prompts)
- `\033[0m`: Reset to default colors

## Key Terminology

- **Wall time**: Real-world elapsed time (what a stopwatch measures), not CPU time
- **Tool**: A function the LLM can invoke to interact with the real world
- **Tool calls**: When the model requests to execute a tool
- **Tool results**: Feedback to the model after tool execution

## Files and Dependencies

### Main Components
- `agents/s01_agent_loop.py`: Core agent loop implementation
- `agents/s02_tool_use.py`: Expands on tool dispatching
- `agents/s03_todo_write.py`: Planning with todo write

### Dependencies
- `langchain_ollama`: For ChatOllama integration
- `python-dotenv`: For environment variable management
- `subprocess`: Built-in Python module for process execution

### Environment Variables
- `OLLAMA_BASE_URL`: Ollama base URL (default: http://192.168.1.25:11434)
- `OLLAMA_MODEL`: Model name (default: qwen3-coder-next:q8_0)
