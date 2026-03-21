# AGENTS.md

This repository teaches harness engineering for AI agents—building the environment (tools, knowledge, context management) that surrounding agent models.

## Project Structure

```
learn-claude-code/
├── agents/               # Python reference implementations (s01-s12 + s_full)
├── web/                  # Next.js interactive learning platform
├── skills/               # Skill files (mcp-builder, pdf, code-review, agent-builder)
├── docs/{en,zh,ja}/      # Documentation in English, Chinese, Japanese
├── tests/                # Python test files
└── .github/workflows/    # CI/CD workflows
```

## Build/Run Commands

### Python Agents

```bash
# Install dependencies
pip install -r requirements.txt
# or
pip install anthropic python-dotenv

# Run a specific agent session
python agents/s01_agent_loop.py       # Agent loop
python agents/s02_tool_use.py         # Tool dispatch
python agents/s03_todo_write.py       # Planning with todo write
python agents/s04_subagent.py         # Subagents
python agents/s05_skill_loading.py    # Skill loading
python agents/s06_context_compact.py  # Context compression
python agents/s07_task_system.py      # Task system
python agents/s08_background_tasks.py # Background tasks
python agents/s09_agent_teams.py      # Agent teams
python agents/s10_team_protocols.py   # Team protocols
python agents/s11_autonomous_agents.py # Autonomous agents
python agents/s12_worktree_task_isolation.py # Worktree isolation
python agents/s_full.py               # Capstone: all mechanisms
```

### Web Platform

```bash
cd web
npm install           # Install dependencies
npm run dev          # Development server (http://localhost:3000)
npm run build        # Build for production
npm run start        # Start production server
npm run extract      # Extract content from agents for web display
```

## Type Checking & Linting

### TypeScript/Web

```bash
cd web
npx tsc --noEmit     # Type check TypeScript files
# Note: No ESLint/Prettier configured
```

### Python

```bash
# No type checking or linting configured for Python agents
# Consider adding mypy and ruff for production use
```

## Testing

### Python Tests

```bash
# Run unit tests
python tests/test_unit.py

# Run session-specific tests (requires API keys)
TEST_API_KEY=xxx TEST_BASE_URL=xxx TEST_MODEL=xxx python tests/test_v0.py
# Supported sessions: v0, v1, v2, v3, v4, v5, v6, v7, v8a, v8b, v8c, v9

# Run all tests (CI pattern)
python tests/test_unit.py && python tests/test_v0.py && ...
```

### Web Tests

```bash
# No test framework configured
# Web platform is tested manually via dev server
```

## Code Style Guidelines

### Python (agents/)

- **Imports**: Standard library first, then third-party (anthropic, dotenv)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Types**: Dynamic typing (no type hints in current code)
- **Error Handling**: Try/except for subprocess timeouts; validation for dangerous commands
- **Formatting**: No configured formatter (PEP 8 recommended)
- **Comments**: Descriptive docstrings for modules/functions
- **Safety**: Block dangerous commands (rm -rf /, sudo, shutdown, reboot)
- **Output**: Color-coded terminal output (yellow for commands, cyan for prompts)

### TypeScript (web/)

- **Imports**: ES modules with alias `@/*` → `./src/*`
- **Naming**: snake_case for files, camelCase for variables/functions, PascalCase for components
- **Types**: TypeScript with strict mode enabled
- **Formatting**: No configured formatter (Prettier recommended)
- **Comments**: Minimal, self-explanatory code
- **React**: Function components with hooks, no class components
- **Styling**: Tailwind CSS (v4), utility-first approach
- **Next.js**: App Router, client components with "use client", export output mode

### General

- **Act, don't explain**: Agent responses should be concise and actionable
- **Single responsibility**: Each session adds one harness mechanism
- **Minimal code**: Focus on core patterns over production-ready code
- **Safety first**: Sandbox file access, block dangerous operations
- **Documentation**: Each agent file has a markdown header explaining the pattern

## Skill Files

Skills are stored in `skills/*/SKILL.md` with YAML frontmatter:

```yaml
---
name: mcp-builder
description: Build MCP servers that give Claude new capabilities
---
```

The file body contains workflows, templates, and best practices.

## Key Patterns

1. **Agent Loop**: while `stop_reason == "tool_use"`: call LLM → execute tools → loop
2. **Tools as hands**: Bash, read, write, edit, glob, grep, browser
3. **Context management**: Subagents, skill loading, compression, task systems
4. **Team coordination**: Async mailboxes, task claiming, worktree isolation
5. **Harness focus**: Build the environment, not the intelligence

## CI/CD

```yaml
# .github/workflows/ci.yml
# - Type check (npx tsc --noEmit)
# - Build (npm run build)

# .github/workflows/test.yml
# - Python unit tests (python tests/test_unit.py)
# - Session tests (python tests/test_v*.py)
# - Web build (cd web && npm run build)
```

## Quick Start

```bash
# For Python agents
pip install -r requirements.txt
cp .env.example .env  # Add ANTHROPIC_API_KEY
python agents/s01_agent_loop.py

# For web platform
cd web
npm install
npm run dev
```

## Important Notes

- The agent is the **model**, the code is the **harness**
- Each session (s01-s12) adds one harness mechanism without changing the core loop
- Skills are loaded on-demand via `tool_result`, not system prompt
- Context compression prevents history from overwhelming the model
- Worktree isolation allows parallel task execution
