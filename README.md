# web-agent

AI-powered browser automation using LLMs and Chrome DevTools Protocol (CDP).

`web-agent` is an async Python library that enables AI agents to autonomously navigate web pages, interact with elements, and complete complex tasks by processing HTML/DOM state and making LLM-driven decisions.

## Features

- **Multi-LLM Support** — OpenAI, Anthropic, Google Gemini, Groq, Ollama, Azure, AWS Bedrock, and more
- **Chrome DevTools Protocol** — Direct browser control via CDP through [cdp-use](https://github.com/web-agent/cdp-use)
- **Event-Driven Architecture** — Modular watchdog system for downloads, popups, security, DOM, and crash handling
- **MCP Integration** — Run as an MCP server for Claude Desktop or connect to external MCP servers
- **Code Agent** — Jupyter-like code execution capabilities for data analysis tasks
- **Cloud Support** — Optional hosted browser instances via web-agent Cloud
- **Sandboxed Execution** — Isolated browser environments for safe automation
- **DOM Serialization** — Intelligent DOM extraction with accessibility tree generation and element highlighting

## Quick Start

### Prerequisites

- Python >= 3.11
- Chrome or Chromium browser
- An LLM API key (Google Gemini, OpenAI, Anthropic, etc.)

### Installation

```bash
# Using uv (recommended)
uv venv --python 3.12
source .venv/bin/activate
uv sync

# Or with pip
pip install web-agent
```

### Environment Setup

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and set your LLM provider key:

```env
GOOGLE_API_KEY=your_google_api_key_here
# or
OPENAI_API_KEY=your_openai_api_key_here
# or
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

If Chrome isn't in your PATH, set the executable path:

```env
web_agent_EXECUTABLE_PATH=/path/to/chrome
```

### Basic Usage

```python
import asyncio
from web_agent import Agent
from web_agent.llm.google import ChatGoogle

async def main():
    llm = ChatGoogle(model="gemini-2.0-flash")
    agent = Agent(
        task="Search Google for 'browser automation' and tell me the top 3 results",
        llm=llm,
    )
    result = await agent.run()
    print(result.final_result())

asyncio.run(main())
```

### Form Filling Example

```python
import asyncio
from web_agent import Agent
from web_agent.llm.google import ChatGoogle

async def main():
    llm = ChatGoogle(model="gemini-2.0-flash")
    agent = Agent(
        task=(
            "Go to https://httpbin.org/forms/post and fill out the form with: "
            "Customer name: John Doe, Telephone: 555-1234, "
            "Email: john@example.com, Size: Medium, "
            "Topping: Cheese. Then submit the form."
        ),
        llm=llm,
    )
    await agent.run()

asyncio.run(main())
```

## CLI

The library includes multiple CLI entry points:

```bash
# Primary CLI commands (all aliases for the same tool)
web-agent <command>
webagent <command>
bu <command>

# Run as MCP server (for Claude Desktop integration)
web-agent --mcp
```

## Architecture

```
web_agent/
├── agent/           # Core agent orchestrator (task loop, LLM interaction)
├── browser/         # Browser session lifecycle, CDP, watchdog services
│   ├── cloud/       # Cloud browser instance management
│   └── watchdogs/   # Downloads, popups, security, DOM, crash handlers
├── dom/             # DOM extraction, serialization, accessibility tree
├── llm/             # Multi-provider LLM abstraction layer
│   ├── google/      # Gemini
│   ├── openai/      # GPT-4o, etc.
│   ├── anthropic/   # Claude
│   ├── groq/        # Groq
│   ├── ollama/      # Local models
│   └── ...          # Azure, AWS, Mistral, DeepSeek, etc.
├── tools/           # Action registry (click, type, scroll, navigate)
├── mcp/             # Model Context Protocol server/client
├── code_use/        # Jupyter-like code execution agent
├── skills/          # Cloud skills API integration
├── sandbox/         # Sandboxed browser execution
└── tokens/          # Token cost tracking and billing
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Agent** | Main orchestrator — takes tasks, manages browser sessions, runs LLM action loop |
| **BrowserSession** | Manages browser lifecycle, CDP connections, coordinates watchdog services via event bus |
| **Tools** | Action registry mapping LLM decisions to browser operations |
| **DomService** | Extracts and processes DOM content, handles element highlighting and a11y tree |
| **LLM Layer** | Unified abstraction across OpenAI, Anthropic, Google, Groq, Ollama, and more |

### Event-Driven Browser Management

BrowserSession uses a [bubus](https://pypi.org/project/bubus/) event bus to coordinate watchdog services:

- **DownloadsWatchdog** — File download handling
- **PopupsWatchdog** — JavaScript dialog management
- **SecurityWatchdog** — Domain restrictions and security policies
- **DOMWatchdog** — DOM snapshots, screenshots, element highlighting
- **CrashWatchdog** — Browser crash detection and recovery

## Development

### Testing

```bash
# Run CI test suite
uv run pytest -vxs tests/ci

# Run specific test file
uv run pytest -vxs tests/ci/test_specific.py

# Run all tests (including integration)
uv run pytest -vxs tests/
```

### Code Quality

```bash
# Type checking
uv run pyright

# Linting and auto-fix
uv run ruff check --fix

# Formatting
uv run ruff format

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Supported Models

| Provider | Models | Env Variable |
|----------|--------|-------------|
| Google | Gemini 2.0 Flash, Gemini Pro | `GOOGLE_API_KEY` |
| OpenAI | GPT-4o, GPT-4o-mini | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5 Sonnet, Claude 3 | `ANTHROPIC_API_KEY` |
| Groq | LLaMA, Mixtral | `GROQ_API_KEY` |
| Ollama | Any local model | (local) |
| Azure | Azure OpenAI models | `AZURE_OPENAI_API_KEY` |
| AWS | Bedrock models | `AWS_ACCESS_KEY_ID` |
| DeepSeek | DeepSeek models | `DEEPSEEK_API_KEY` |

## Roadmap

- **Vision Pipeline Optimization** — Enhanced screenshot and visual element processing for better LLM understanding
- **RAG-Based Navigation** — Pre-defined reference documents for complex workflows (flight booking, multi-step forms) that the model can use as guides
- **mem0-Inspired Context System** — High-context history management for long-running agent sessions with persistent memory across tasks

## Configuration

See [.env.example](.env.example) for all available configuration options including:

- Logging levels and file paths
- LLM provider API keys
- Browser executable path and headless mode
- Proxy configuration
- Telemetry settings

## License

MIT License — see [LICENSE](LICENSE) for details.
