---
name: web-agent
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages.
allowed-tools: Bash(web-agent:*)
---

# Browser Automation with web-agent CLI

The `web-agent` command provides fast, persistent browser automation. It maintains browser sessions across commands, enabling complex multi-step workflows.

## Installation

```bash
# Run without installing (recommended for one-off use)
uvx "web-agent[cli]" open https://example.com

# Or install permanently
uv pip install "web-agent[cli]"

# Install browser dependencies (Chromium)
web-agent install
```

## Setup

**One-line install (recommended)**
```bash
curl -fsSL https://web-agent.com/cli/install.sh | bash
```

This interactive installer lets you choose your installation mode and configures everything automatically.

**Installation modes:**
```bash
curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --remote-only  # Cloud browser only
curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --local-only   # Local browser only
curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --full         # All modes
```

| Install Mode | Available Browsers | Default | Use Case |
|--------------|-------------------|---------|----------|
| `--remote-only` | remote | remote | Sandboxed agents, CI, no GUI |
| `--local-only` | chromium, real | chromium | Local development |
| `--full` | chromium, real, remote | chromium | Full flexibility |

When only one mode is installed, it becomes the default and no `--browser` flag is needed.

**Pass API key during install:**
```bash
curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --remote-only --api-key bu_xxx
```

**Verify installation:**
```bash
web-agent doctor
```

**Setup wizard (first-time configuration):**
```bash
web-agent setup                         # Interactive setup
web-agent setup --mode local            # Configure for local browser only
web-agent setup --mode remote           # Configure for cloud browser only
web-agent setup --mode full             # Configure all modes
web-agent setup --api-key bu_xxx        # Set API key during setup
web-agent setup --yes                   # Skip interactive prompts
```

**Generate template files:**
```bash
web-agent init                          # Interactive template selection
web-agent init --list                   # List available templates
web-agent init --template basic         # Generate specific template
web-agent init --output my_script.py    # Specify output file
web-agent init --force                  # Overwrite existing files
```

**Manual cloudflared install (for tunneling):**
```bash
# macOS:
brew install cloudflared

# Linux:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/.local/bin/cloudflared && chmod +x ~/.local/bin/cloudflared

# Windows:
winget install Cloudflare.cloudflared
```

## Quick Start

```bash
web-agent open https://example.com           # Navigate to URL
web-agent state                              # Get page elements with indices
web-agent click 5                            # Click element by index
web-agent type "Hello World"                 # Type text
web-agent screenshot                         # Take screenshot
web-agent close                              # Close browser
```

## Core Workflow

1. **Navigate**: `web-agent open <url>` - Opens URL (starts browser if needed)
2. **Inspect**: `web-agent state` - Returns clickable elements with indices
3. **Interact**: Use indices from state to interact (`web-agent click 5`, `web-agent input 3 "text"`)
4. **Verify**: `web-agent state` or `web-agent screenshot` to confirm actions
5. **Repeat**: Browser stays open between commands

## Browser Modes

```bash
web-agent --browser chromium open <url>      # Default: headless Chromium
web-agent --browser chromium --headed open <url>  # Visible Chromium window
web-agent --browser real open <url>          # User's Chrome with login sessions
web-agent --browser remote open <url>        # Cloud browser (requires API key)
```

- **chromium**: Fast, isolated, headless by default
- **real**: Uses your Chrome with cookies, extensions, logged-in sessions
- **remote**: Cloud-hosted browser with proxy support (requires web_agent_API_KEY)

## Commands

### Navigation
```bash
web-agent open <url>                    # Navigate to URL
web-agent back                          # Go back in history
web-agent scroll down                   # Scroll down
web-agent scroll up                     # Scroll up
web-agent scroll down --amount 1000     # Scroll by specific pixels (default: 500)
```

### Page State
```bash
web-agent state                         # Get URL, title, and clickable elements
web-agent screenshot                    # Take screenshot (outputs base64)
web-agent screenshot path.png           # Save screenshot to file
web-agent screenshot --full path.png    # Full page screenshot
```

### Interactions (use indices from `web-agent state`)
```bash
web-agent click <index>                 # Click element
web-agent type "text"                   # Type text into focused element
web-agent input <index> "text"          # Click element, then type text
web-agent keys "Enter"                  # Send keyboard keys
web-agent keys "Control+a"              # Send key combination
web-agent select <index> "option"       # Select dropdown option
```

### Tab Management
```bash
web-agent switch <tab>                  # Switch to tab by index
web-agent close-tab                     # Close current tab
web-agent close-tab <tab>               # Close specific tab
```

### JavaScript & Data
```bash
web-agent eval "document.title"         # Execute JavaScript, return result
web-agent extract "all product prices"  # Extract data using LLM (requires API key)
```

### Cookies
```bash
web-agent cookies get                   # Get all cookies
web-agent cookies get --url <url>       # Get cookies for specific URL
web-agent cookies set <name> <value>    # Set a cookie
web-agent cookies set name val --domain .example.com --secure --http-only
web-agent cookies set name val --same-site Strict  # SameSite: Strict, Lax, or None
web-agent cookies set name val --expires 1735689600  # Expiration timestamp
web-agent cookies clear                 # Clear all cookies
web-agent cookies clear --url <url>     # Clear cookies for specific URL
web-agent cookies export <file>         # Export all cookies to JSON file
web-agent cookies export <file> --url <url>  # Export cookies for specific URL
web-agent cookies import <file>         # Import cookies from JSON file
```

### Wait Conditions
```bash
web-agent wait selector "h1"            # Wait for element to be visible
web-agent wait selector ".loading" --state hidden  # Wait for element to disappear
web-agent wait selector "#btn" --state attached    # Wait for element in DOM
web-agent wait text "Success"           # Wait for text to appear
web-agent wait selector "h1" --timeout 5000  # Custom timeout in ms
```

### Additional Interactions
```bash
web-agent hover <index>                 # Hover over element (triggers CSS :hover)
web-agent dblclick <index>              # Double-click element
web-agent rightclick <index>            # Right-click element (context menu)
```

### Information Retrieval
```bash
web-agent get title                     # Get page title
web-agent get html                      # Get full page HTML
web-agent get html --selector "h1"      # Get HTML of specific element
web-agent get text <index>              # Get text content of element
web-agent get value <index>             # Get value of input/textarea
web-agent get attributes <index>        # Get all attributes of element
web-agent get bbox <index>              # Get bounding box (x, y, width, height)
```

### Python Execution (Persistent Session)
```bash
web-agent python "x = 42"               # Set variable
web-agent python "print(x)"             # Access variable (outputs: 42)
web-agent python "print(browser.url)"   # Access browser object
web-agent python --vars                 # Show defined variables
web-agent python --reset                # Clear Python namespace
web-agent python --file script.py       # Execute Python file
```

The Python session maintains state across commands. The `browser` object provides:
- `browser.url` - Current page URL
- `browser.title` - Page title
- `browser.html` - Get page HTML
- `browser.goto(url)` - Navigate
- `browser.click(index)` - Click element
- `browser.type(text)` - Type text
- `browser.input(index, text)` - Click element, then type
- `browser.keys(keys)` - Send keyboard keys (e.g., "Enter", "Control+a")
- `browser.screenshot(path)` - Take screenshot
- `browser.scroll(direction, amount)` - Scroll page
- `browser.back()` - Go back in history
- `browser.wait(seconds)` - Sleep/pause execution
- `browser.extract(query)` - Extract data using LLM

### Agent Tasks (Requires API Key)
```bash
web-agent run "Fill the contact form with test data"    # Run AI agent
web-agent run "Extract all product prices" --max-steps 50
```

Agent tasks use an LLM to autonomously complete complex browser tasks. Requires `web_agent_API_KEY` or configured LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc).

#### Remote Mode Agent Options

When using `--browser remote`, additional options are available:

```bash
# Basic remote task (uses US proxy by default)
web-agent -b remote run "Search for AI news"

# Specify LLM model
web-agent -b remote run "task" --llm gpt-4o
web-agent -b remote run "task" --llm claude-sonnet-4-20250514
web-agent -b remote run "task" --llm gemini-2.0-flash

# Proxy configuration (default: us)
web-agent -b remote run "task" --proxy-country gb    # UK proxy
web-agent -b remote run "task" --proxy-country de    # Germany proxy

# Session reuse (run multiple tasks in same browser session)
web-agent -b remote run "task 1" --keep-alive
# Returns: session_id: abc-123
web-agent -b remote run "task 2" --session-id abc-123

# Execution modes
web-agent -b remote run "task" --no-wait     # Async, returns task_id immediately
web-agent -b remote run "task" --stream      # Stream status updates
web-agent -b remote run "task" --flash       # Fast execution mode

# Advanced options
web-agent -b remote run "task" --thinking    # Extended reasoning mode
web-agent -b remote run "task" --vision      # Enable vision (default)
web-agent -b remote run "task" --no-vision   # Disable vision
web-agent -b remote run "task" --wait        # Wait for completion (default: async)

# Use cloud profile (preserves cookies across sessions)
web-agent -b remote run "task" --profile <cloud-profile-id>

# Task configuration
web-agent -b remote run "task" --start-url https://example.com  # Start from specific URL
web-agent -b remote run "task" --allowed-domain example.com     # Restrict navigation (repeatable)
web-agent -b remote run "task" --metadata key=value             # Task metadata (repeatable)
web-agent -b remote run "task" --secret API_KEY=xxx             # Task secrets (repeatable)
web-agent -b remote run "task" --skill-id skill-123             # Enable skills (repeatable)

# Structured output and evaluation
web-agent -b remote run "task" --structured-output '{"type":"object"}'  # JSON schema for output
web-agent -b remote run "task" --judge                 # Enable judge mode
web-agent -b remote run "task" --judge-ground-truth "expected answer"   # Expected answer for judge
```

### Task Management (Remote Mode)

Manage cloud tasks when using remote mode:

```bash
web-agent task list                     # List recent tasks
web-agent task list --limit 20          # Show more tasks
web-agent task list --status running    # Filter by status
web-agent task list --session <id>      # Filter by session ID
web-agent task list --json              # JSON output

web-agent task status <task-id>         # Get task status (token efficient)
web-agent task status <task-id> -c      # Show all steps with reasoning
web-agent task status <task-id> -v      # Show all steps with URLs + actions
web-agent task status <task-id> --last 5  # Show only last 5 steps
web-agent task status <task-id> --step 3  # Show specific step number
web-agent task status <task-id> --reverse # Show steps newest first

web-agent task stop <task-id>           # Stop a running task
web-agent task logs <task-id>           # Get task execution logs
```

**Token-efficient monitoring:** Default `task status` shows only the latest step. Use `-c` (compact) or `-v` (verbose) only when you need more context.

### Cloud Session Management (Remote Mode)

Manage cloud browser sessions:

```bash
web-agent session list                  # List cloud sessions
web-agent session list --limit 20       # Show more sessions
web-agent session list --status active  # Filter by status
web-agent session list --json           # JSON output

web-agent session get <session-id>      # Get session details
web-agent session get <session-id> --json

web-agent session stop <session-id>     # Stop a session
web-agent session stop --all            # Stop all active sessions

# Create a new cloud session manually
web-agent session create                          # Create with defaults
web-agent session create --profile <id>           # With cloud profile
web-agent session create --proxy-country gb       # With geographic proxy
web-agent session create --start-url https://example.com  # Start at URL
web-agent session create --screen-size 1920x1080  # Custom screen size
web-agent session create --keep-alive             # Keep session alive
web-agent session create --persist-memory         # Persist memory between tasks

# Share session publicly (for collaboration/debugging)
web-agent session share <session-id>    # Create public share URL
web-agent session share <session-id> --delete  # Delete public share
```

## Exposing Local Dev Servers

If you're running a dev server locally and need a cloud browser to reach it, use Cloudflare tunnels:

```bash
# Start your dev server
npm run dev &  # localhost:3000

# Expose it via Cloudflare tunnel
web-agent tunnel 3000
# → url: https://abc.trycloudflare.com

# Now the cloud browser can reach your local server
web-agent --browser remote open https://abc.trycloudflare.com
```

**Tunnel commands:**
```bash
web-agent tunnel <port>           # Start tunnel (returns URL)
web-agent tunnel <port>           # Idempotent - returns existing URL
web-agent tunnel list             # Show active tunnels
web-agent tunnel stop <port>      # Stop tunnel
web-agent tunnel stop --all       # Stop all tunnels
```

**Note:** Tunnels are independent of browser sessions. They persist across `web-agent close` and can be managed separately.

Cloudflared is installed by `install.sh`. If missing, install manually (see Setup section).

## Running Subagents (Remote Mode)

Cloud sessions and tasks provide a powerful model for running **subagents** - autonomous browser agents that execute tasks in parallel.

### Key Concepts

- **Session = Agent**: Each cloud session is a browser agent with its own state (cookies, tabs, history)
- **Task = Work**: Tasks are jobs given to an agent. An agent can run multiple tasks sequentially
- **Parallel agents**: Run multiple sessions simultaneously for parallel work
- **Session reuse**: While a session is alive, you can assign it more tasks
- **Session lifecycle**: Once stopped, a session cannot be revived - start a new one

### Basic Subagent Workflow

```bash
# 1. Start a subagent task (creates new session automatically)
web-agent -b remote run "Search for AI news and summarize top 3 articles" --no-wait
# Returns: task_id: task-abc, session_id: sess-123

# 2. Check task progress
web-agent task status task-abc
# Shows: Status: running, or finished with output

# 3. View execution logs
web-agent task logs task-abc
```

### Running Parallel Subagents

Launch multiple agents to work simultaneously:

```bash
# Start 3 parallel research agents
web-agent -b remote run "Research competitor A pricing" --no-wait
# → task_id: task-1, session_id: sess-a

web-agent -b remote run "Research competitor B pricing" --no-wait
# → task_id: task-2, session_id: sess-b

web-agent -b remote run "Research competitor C pricing" --no-wait
# → task_id: task-3, session_id: sess-c

# Monitor all running tasks
web-agent task list --status running
# Shows all 3 tasks with their status

# Check individual task results as they complete
web-agent task status task-1
web-agent task status task-2
web-agent task status task-3
```

### Reusing an Agent for Multiple Tasks

Keep a session alive to run sequential tasks in the same browser context:

```bash
# Start first task, keep session alive
web-agent -b remote run "Log into example.com" --keep-alive --no-wait
# → task_id: task-1, session_id: sess-123

# Wait for login to complete...
web-agent task status task-1
# → Status: finished

# Give the same agent another task (reuses login session)
web-agent -b remote run "Navigate to settings and export data" --session-id sess-123 --no-wait
# → task_id: task-2, session_id: sess-123 (same session!)

# Agent retains cookies, login state, etc. from previous task
```

### Managing Active Agents

```bash
# List all active agents (sessions)
web-agent session list --status active
# Shows: sess-123 [active], sess-456 [active], ...

# Get details on a specific agent
web-agent session get sess-123
# Shows: status, started time, live URL for viewing

# Stop a specific agent
web-agent session stop sess-123

# Stop all agents at once
web-agent session stop --all
```

### Stopping Tasks vs Sessions

```bash
# Stop a running task (session may continue if --keep-alive was used)
web-agent task stop task-abc

# Stop an entire agent/session (terminates all its tasks)
web-agent session stop sess-123
```

### Custom Agent Configuration

```bash
# Default: US proxy, auto LLM selection
web-agent -b remote run "task" --no-wait

# Explicit configuration
web-agent -b remote run "task" \
  --llm gpt-4o \
  --proxy-country gb \
  --keep-alive \
  --no-wait

# With cloud profile (preserves cookies across sessions)
web-agent -b remote run "task" --profile <profile-id> --no-wait
```

### Monitoring Subagents

**Task status is designed for token efficiency.** Default output is minimal - only expand when needed:

| Mode | Flag | Tokens | Use When |
|------|------|--------|----------|
| Default | (none) | Low | Polling progress |
| Compact | `-c` | Medium | Need full reasoning |
| Verbose | `-v` | High | Debugging actions |

**Recommended workflow:**

```bash
# 1. Launch task
web-agent -b remote run "task" --no-wait
# → task_id: abc-123

# 2. Poll with default (token efficient) - only latest step
web-agent task status abc-123
# ✅ abc-123... [finished] $0.009 15s
#   ... 1 earlier steps
#   2. I found the information and extracted...

# 3. ONLY IF task failed or need context: use --compact
web-agent task status abc-123 -c

# 4. ONLY IF debugging specific actions: use --verbose
web-agent task status abc-123 -v
```

**For long tasks (50+ steps):**
```bash
web-agent task status <id> -c --last 5   # Last 5 steps only
web-agent task status <id> -c --reverse  # Newest first
web-agent task status <id> -v --step 10  # Inspect specific step
```

**Live view**: Watch an agent work in real-time:
```bash
web-agent session get <session-id>
# → Live URL: https://live.web-agent.com?wss=...
# Open this URL in your browser to watch the agent
```

**Detect stuck tasks**: If cost/duration stops increasing, the task may be stuck:
```bash
web-agent task status <task-id>
# 🔄 abc-123... [started] $0.009 45s  ← if cost doesn't change, task is stuck
```

**Logs**: Only available after task completes:
```bash
web-agent task logs <task-id>  # Works after task finishes
```

### Cleanup

Always clean up sessions after parallel work:
```bash
# Stop all active agents
web-agent session stop --all

# Or stop specific sessions
web-agent session stop <session-id>
```

### Troubleshooting Subagents

**Session reuse fails after `task stop`**:
If you stop a task and try to reuse its session, the new task may get stuck at "created" status. Solution: create a new agent instead.
```bash
# This may fail:
web-agent task stop <task-id>
web-agent -b remote run "new task" --session-id <same-session>  # Might get stuck

# Do this instead:
web-agent -b remote run "new task" --profile <profile-id>  # Fresh session
```

**Task stuck at "started"**:
- Check cost with `task status` - if not increasing, task is stuck
- View live URL with `session get` to see what's happening
- Stop the task and create a new agent

**Sessions persist after tasks complete**:
Tasks finishing doesn't auto-stop sessions. Clean up manually:
```bash
web-agent session list --status active  # See lingering sessions
web-agent session stop --all            # Clean up
```

### Session Management
```bash
web-agent sessions                      # List active sessions
web-agent close                         # Close current session
web-agent close --all                   # Close all sessions
```

### Profile Management

#### Local Chrome Profiles (`--browser real`)
```bash
web-agent -b real profile list          # List local Chrome profiles
```

**Before opening a real browser (`--browser real`)**, always ask the user if they want to use a specific Chrome profile or no profile. Use `profile list` to show available profiles:

```bash
web-agent -b real profile list
# Output: Default: Person 1 (user@gmail.com)
#         Profile 1: Work (work@company.com)

# With a specific profile (has that profile's cookies/logins)
web-agent --browser real --profile "Profile 1" open https://gmail.com

# Without a profile (fresh browser, no existing logins)
web-agent --browser real open https://gmail.com

# Headless mode (no visible window) - useful for cookie export
web-agent --browser real --profile "Default" cookies export /tmp/cookies.json
```

Each Chrome profile has its own cookies, history, and logged-in sessions. Choosing the right profile determines whether sites will be pre-authenticated.

#### Cloud Profiles (`--browser remote`)

Cloud profiles store browser state (cookies) in web-agent Cloud, persisting across sessions. Requires `web_agent_API_KEY`.

```bash
web-agent -b remote profile list            # List cloud profiles
web-agent -b remote profile list --page 2 --page-size 50  # Pagination
web-agent -b remote profile get <id>        # Get profile details
web-agent -b remote profile create          # Create new cloud profile
web-agent -b remote profile create --name "My Profile"  # Create with name
web-agent -b remote profile update <id> --name "New"    # Rename profile
web-agent -b remote profile delete <id>     # Delete profile
```

Use a cloud profile with `--browser remote --profile <id>`:

```bash
web-agent --browser remote --profile abc-123 open https://example.com
```

### Syncing Cookies to Cloud

**⚠️ IMPORTANT: Before syncing cookies from a local browser to the cloud, the agent MUST:**
1. Ask the user which local Chrome profile to use (`web-agent -b real profile list`)
2. Ask which domain(s) to sync - do NOT default to syncing the full profile
3. Confirm before proceeding

**Default behavior:** Create a NEW cloud profile for each domain sync. This ensures clear separation of concerns for cookies. Users can add cookies to existing profiles if needed.

**Step 1: List available profiles and cookies**

```bash
# List local Chrome profiles
web-agent -b real profile list
# → Default: Person 1 (user@gmail.com)
# → Profile 1: Work (work@company.com)

# See what cookies are in a profile
web-agent -b real profile cookies "Default"
# → youtube.com: 23
# → google.com: 18
# → github.com: 2
```

**Step 2: Sync cookies (three levels of control)**

**1. Domain-specific sync (recommended default)**
```bash
web-agent profile sync --from "Default" --domain youtube.com
# Creates new cloud profile: "Chrome - Default (youtube.com)"
# Only syncs youtube.com cookies
```
This is the recommended approach - sync only the cookies you need.

**2. Full profile sync (use with caution)**
```bash
web-agent profile sync --from "Default"
# Syncs ALL cookies from the profile
```
⚠️ **Warning:** This syncs ALL cookies including sensitive data, tracking cookies, session tokens for every site, etc. Only use when the user explicitly needs their entire browser state.

**3. Fine-grained control (advanced)**
```bash
# Export cookies to file
web-agent --browser real --profile "Default" cookies export /tmp/cookies.json

# Manually edit the JSON to keep only specific cookies

# Import to cloud profile
web-agent --browser remote --profile <id> cookies import /tmp/cookies.json
```
For users who need individual cookie-level control.

**Step 3: Use the synced profile**

```bash
web-agent --browser remote --profile <id> open https://youtube.com
```

**Adding cookies to existing profiles:**
```bash
# Sync additional domain to existing profile
web-agent --browser real --profile "Default" cookies export /tmp/cookies.json
web-agent --browser remote --profile <existing-id> cookies import /tmp/cookies.json
```

**Managing profiles:**
```bash
web-agent profile update <id> --name "New Name"  # Rename
web-agent profile delete <id>                    # Delete
```

### Server Control
```bash
web-agent server status                 # Check if server is running
web-agent server stop                   # Stop server
web-agent server logs                   # View server logs
```

### Setup
```bash
web-agent install                       # Install Chromium and system dependencies
```

## Global Options

| Option | Description |
|--------|-------------|
| `--session NAME` | Use named session (default: "default") |
| `--browser MODE` | Browser mode: chromium, real, remote |
| `--headed` | Show browser window (chromium mode) |
| `--profile NAME` | Browser profile (local name or cloud ID) |
| `--json` | Output as JSON |
| `--api-key KEY` | Override API key |
| `--mcp` | Run as MCP server via stdin/stdout |

**Session behavior**: All commands without `--session` use the same "default" session. The browser stays open and is reused across commands. Use `--session NAME` to run multiple browsers in parallel.

## API Key Configuration

Some features (`run`, `extract`, `--browser remote`) require an API key. The CLI checks these locations in order:

1. `--api-key` command line flag
2. `web_agent_API_KEY` environment variable
3. `~/.config/web-agent/config.json` file

To configure permanently:
```bash
mkdir -p ~/.config/web-agent
echo '{"api_key": "your-key-here"}' > ~/.config/web-agent/config.json
```

## Examples

### Form Submission
```bash
web-agent open https://example.com/contact
web-agent state
# Shows: [0] input "Name", [1] input "Email", [2] textarea "Message", [3] button "Submit"
web-agent input 0 "John Doe"
web-agent input 1 "john@example.com"
web-agent input 2 "Hello, this is a test message."
web-agent click 3
web-agent state  # Verify success
```

### Multi-Session Workflows
```bash
web-agent --session work open https://work.example.com
web-agent --session personal open https://personal.example.com
web-agent --session work state    # Check work session
web-agent --session personal state  # Check personal session
web-agent close --all             # Close both sessions
```

### Data Extraction with Python
```bash
web-agent open https://example.com/products
web-agent python "
products = []
for i in range(20):
    browser.scroll('down')
browser.screenshot('products.png')
"
web-agent python "print(f'Captured {len(products)} products')"
```

### Using Real Browser (Logged-In Sessions)
```bash
web-agent --browser real open https://gmail.com
# Uses your actual Chrome with existing login sessions
web-agent state  # Already logged in!
```

## Common Patterns

### Test a Local Dev Server with Cloud Browser

```bash
# Start dev server
npm run dev &  # localhost:3000

# Tunnel it
web-agent tunnel 3000
# → url: https://abc.trycloudflare.com

# Browse with cloud browser
web-agent --browser remote open https://abc.trycloudflare.com
web-agent state
web-agent screenshot
```

### Screenshot Loop for Visual Verification

```bash
web-agent open https://example.com
for i in 1 2 3 4 5; do
  web-agent scroll down
  web-agent screenshot "page_$i.png"
done
```

## Tips

1. **Always run `web-agent state` first** to see available elements and their indices
2. **Use `--headed` for debugging** to see what the browser is doing
3. **Sessions persist** - the browser stays open between commands
4. **Use `--json` for parsing** output programmatically
5. **Python variables persist** across `web-agent python` commands within a session
6. **Real browser mode** preserves your login sessions and extensions
7. **CLI aliases**: `bu`, `browser`, and `webagent` all work identically to `web-agent`

## Troubleshooting

**Run diagnostics first:**
```bash
web-agent doctor                    # Check installation status
```

**Browser won't start?**
```bash
web-agent install                   # Install/reinstall Chromium
web-agent server stop               # Stop any stuck server
web-agent --headed open <url>       # Try with visible window
```

**Element not found?**
```bash
web-agent state                     # Check current elements
web-agent scroll down               # Element might be below fold
web-agent state                     # Check again
```

**Session issues?**
```bash
web-agent sessions                  # Check active sessions
web-agent close --all               # Clean slate
web-agent open <url>                # Fresh start
```

## Cleanup

**Always close the browser when done.** Run this after completing browser automation:

```bash
web-agent close
```
