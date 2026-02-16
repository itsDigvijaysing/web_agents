---
name: remote-browser
description: Controls a cloud browser from a sandboxed remote machine. Use when the agent is running in a sandbox (no GUI) and needs to navigate websites, interact with web pages, fill forms, take screenshots, or expose local dev servers via tunnels.
allowed-tools: Bash(web-agent:*)
---

# Remote Browser Automation for Sandboxed Agents

This skill is for agents running on **sandboxed remote machines** (cloud VMs, CI, coding agents) that need to control a browser. Install `web-agent` and drive a cloud browser — no local Chrome needed.

## Setup

**Remote-only install (recommended for sandboxed agents)**
```bash
curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --remote-only
```

This configures web-agent to only use cloud browsers:
- No Chromium download (~300MB saved)
- `web-agent open <url>` automatically uses remote mode (no `--browser` flag needed)
- If API key is available, you can also pass it during install:
  ```bash
  curl -fsSL https://web-agent.com/cli/install.sh | bash -s -- --remote-only --api-key bu_xxx
  ```

**Manual install (alternative)**
```bash
pip install "web-agent[cli]"

# Install cloudflared for tunneling:
# macOS:
brew install cloudflared

# Linux:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/.local/bin/cloudflared && chmod +x ~/.local/bin/cloudflared

# Windows:
winget install Cloudflare.cloudflared
```

**Then configure your API key:**
```bash
export web_agent_API_KEY=bu_xxx   # Required for cloud browser
```

**Verify installation:**
```bash
web-agent doctor
```

## Core Workflow

When installed with `--remote-only`, commands automatically use the cloud browser — no `--browser` flag needed:

```bash
# Step 1: Start session (automatically uses remote mode)
web-agent open https://example.com
# Returns: url, live_url (view the browser in real-time)

# Step 2+: All subsequent commands use the existing session
web-agent state                   # Get page elements with indices
web-agent click 5                 # Click element by index
web-agent type "Hello World"      # Type into focused element
web-agent input 3 "text"          # Click element, then type
web-agent screenshot              # Take screenshot (base64)
web-agent screenshot page.png     # Save screenshot to file

# Done: Close the session
web-agent close                   # Close browser and release resources
```

### Understanding Installation Modes

| Install Command | Available Modes | Default Mode | Use Case |
|-----------------|-----------------|--------------|----------|
| `--remote-only` | remote | remote | Sandboxed agents, no GUI |
| `--local-only` | chromium, real | chromium | Local development |
| `--full` | chromium, real, remote | chromium | Full flexibility |

When only one mode is installed, it becomes the default and no `--browser` flag is needed.

## Exposing Local Dev Servers

If you're running a dev server on the remote machine and need the cloud browser to reach it:

```bash
# Start your dev server
python -m http.server 3000 &

# Expose it via Cloudflare tunnel
web-agent tunnel 3000
# → url: https://abc.trycloudflare.com

# Now the cloud browser can reach your local server
web-agent open https://abc.trycloudflare.com
```

Tunnel commands:
```bash
web-agent tunnel <port>           # Start tunnel (returns URL)
web-agent tunnel <port>           # Idempotent - returns existing URL
web-agent tunnel list             # Show active tunnels
web-agent tunnel stop <port>      # Stop tunnel
web-agent tunnel stop --all       # Stop all tunnels
```

**Note:** Tunnels are independent of browser sessions. They persist across `web-agent close` and can be managed separately.

Cloudflared is installed by `install.sh --remote-only`. If missing, install manually (see Setup section).

## Commands

### Navigation
```bash
web-agent open <url>              # Navigate to URL
web-agent back                    # Go back in history
web-agent scroll down             # Scroll down
web-agent scroll up               # Scroll up
web-agent scroll down --amount 1000  # Scroll by specific pixels (default: 500)
```

### Page State
```bash
web-agent state                   # Get URL, title, and clickable elements
web-agent screenshot              # Take screenshot (base64)
web-agent screenshot path.png     # Save screenshot to file
web-agent screenshot --full p.png # Full page screenshot
```

### Interactions (use indices from `state`)
```bash
web-agent click <index>           # Click element
web-agent type "text"             # Type into focused element
web-agent input <index> "text"    # Click element, then type
web-agent keys "Enter"            # Send keyboard keys
web-agent keys "Control+a"        # Key combination
web-agent select <index> "option" # Select dropdown option
web-agent hover <index>           # Hover over element
web-agent dblclick <index>        # Double-click
web-agent rightclick <index>      # Right-click
```

### JavaScript & Data
```bash
web-agent eval "document.title"   # Execute JavaScript
web-agent extract "all prices"    # Extract data using LLM
web-agent get title               # Get page title
web-agent get html                # Get page HTML
web-agent get html --selector "h1"  # Scoped HTML
web-agent get text <index>        # Get element text
web-agent get value <index>       # Get input value
web-agent get attributes <index>  # Get element attributes
web-agent get bbox <index>        # Get bounding box (x, y, width, height)
```

### Wait Conditions
```bash
web-agent wait selector "h1"                         # Wait for element
web-agent wait selector ".loading" --state hidden    # Wait for element to disappear
web-agent wait text "Success"                        # Wait for text
web-agent wait selector "#btn" --timeout 5000        # Custom timeout (ms)
```

### Cookies
```bash
web-agent cookies get             # Get all cookies
web-agent cookies get --url <url> # Get cookies for specific URL
web-agent cookies set <name> <val>  # Set a cookie
web-agent cookies set name val --domain .example.com --secure  # With options
web-agent cookies set name val --same-site Strict  # SameSite: Strict, Lax, None
web-agent cookies set name val --expires 1735689600  # Expiration timestamp
web-agent cookies clear           # Clear all cookies
web-agent cookies clear --url <url>  # Clear cookies for specific URL
web-agent cookies export <file>   # Export to JSON
web-agent cookies import <file>   # Import from JSON
```

### Tab Management
```bash
web-agent switch <tab>            # Switch tab by index
web-agent close-tab               # Close current tab
web-agent close-tab <tab>         # Close specific tab
```

### Python Execution (Persistent Session)
```bash
web-agent python "x = 42"           # Set variable
web-agent python "print(x)"         # Access variable (prints: 42)
web-agent python "print(browser.url)"  # Access browser object
web-agent python --vars             # Show defined variables
web-agent python --reset            # Clear namespace
web-agent python --file script.py   # Run Python file
```

The Python session maintains state across commands. The `browser` object provides:
- `browser.url` - Current page URL
- `browser.title` - Page title
- `browser.html` - Get page HTML
- `browser.goto(url)` - Navigate
- `browser.click(index)` - Click element
- `browser.type(text)` - Type text
- `browser.input(index, text)` - Click element, then type
- `browser.keys(keys)` - Send keyboard keys
- `browser.screenshot(path)` - Take screenshot
- `browser.scroll(direction, amount)` - Scroll page
- `browser.back()` - Go back in history
- `browser.wait(seconds)` - Sleep/pause execution
- `browser.extract(query)` - Extract data using LLM

### Agent Tasks
```bash
web-agent run "Fill the contact form with test data"   # AI agent
web-agent run "Extract all product prices" --max-steps 50

# Specify LLM model
web-agent run "task" --llm gpt-4o
web-agent run "task" --llm claude-sonnet-4-20250514
web-agent run "task" --llm gemini-2.0-flash

# Proxy configuration (default: us)
web-agent run "task" --proxy-country gb    # UK proxy
web-agent run "task" --proxy-country de    # Germany proxy

# Session reuse (run multiple tasks in same browser session)
web-agent run "task 1" --keep-alive
# Returns: session_id: abc-123
web-agent run "task 2" --session-id abc-123

# Execution modes
web-agent run "task" --no-wait     # Async, returns task_id immediately
web-agent run "task" --wait        # Wait for completion
web-agent run "task" --stream      # Stream status updates
web-agent run "task" --flash       # Fast execution mode

# Advanced options
web-agent run "task" --thinking    # Extended reasoning mode
web-agent run "task" --vision      # Enable vision (default)
web-agent run "task" --no-vision   # Disable vision

# Use cloud profile (preserves cookies across sessions)
web-agent run "task" --profile <cloud-profile-id>

# Task configuration
web-agent run "task" --start-url https://example.com  # Start from specific URL
web-agent run "task" --allowed-domain example.com     # Restrict navigation (repeatable)
web-agent run "task" --metadata key=value             # Task metadata (repeatable)
web-agent run "task" --secret API_KEY=xxx             # Task secrets (repeatable)
web-agent run "task" --skill-id skill-123             # Enable skills (repeatable)

# Structured output and evaluation
web-agent run "task" --structured-output '{"type":"object"}'  # JSON schema for output
web-agent run "task" --judge                          # Enable judge mode
web-agent run "task" --judge-ground-truth "answer"    # Expected answer for judge
```

### Task Management

Manage cloud tasks:

```bash
web-agent task list                     # List recent tasks
web-agent task list --limit 20          # Show more tasks
web-agent task list --status running    # Filter by status
web-agent task list --status finished
web-agent task list --session <id>      # Filter by session ID
web-agent task list --json              # JSON output

web-agent task status <task-id>         # Get task status (latest step only)
web-agent task status <task-id> -c      # Compact: all steps with reasoning
web-agent task status <task-id> -v      # Verbose: full details with URLs + actions
web-agent task status <task-id> --last 5   # Show only last 5 steps
web-agent task status <task-id> --step 3   # Show specific step number
web-agent task status <task-id> --reverse  # Show steps newest first
web-agent task status <task-id> --json

web-agent task stop <task-id>           # Stop a running task

web-agent task logs <task-id>           # Get task execution logs
```

### Cloud Session Management

Manage cloud browser sessions:

```bash
web-agent session list                  # List cloud sessions
web-agent session list --limit 20       # Show more sessions
web-agent session list --status active  # Filter by status
web-agent session list --json           # JSON output

web-agent session get <session-id>      # Get session details + live URL
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

### Cloud Profile Management

Cloud profiles store browser state (cookies) persistently across sessions. Use profiles to maintain login sessions.

```bash
web-agent profile list                  # List cloud profiles
web-agent profile list --page 2 --page-size 50  # Pagination
web-agent profile get <id>              # Get profile details
web-agent profile create                # Create new profile
web-agent profile create --name "My Profile"  # Create with name
web-agent profile update <id> --name "New Name"  # Rename profile
web-agent profile delete <id>           # Delete profile
```

**Using profiles:**
```bash
# Run task with profile (preserves cookies)
web-agent run "Log into site" --profile <profile-id> --keep-alive

# Create session with profile
web-agent session create --profile <profile-id>

# Open URL with profile
web-agent open https://example.com --profile <profile-id>
```

**Import cookies to cloud profile:**
```bash
# Export cookies from current session
web-agent cookies export /tmp/cookies.json

# Import to cloud profile
web-agent cookies import /tmp/cookies.json --profile <profile-id>
```

## Running Subagents

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
web-agent run "Search for AI news and summarize top 3 articles" --no-wait
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
web-agent run "Research competitor A pricing" --no-wait
# → task_id: task-1, session_id: sess-a

web-agent run "Research competitor B pricing" --no-wait
# → task_id: task-2, session_id: sess-b

web-agent run "Research competitor C pricing" --no-wait
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
web-agent run "Log into example.com" --keep-alive --no-wait
# → task_id: task-1, session_id: sess-123

# Wait for login to complete...
web-agent task status task-1
# → Status: finished

# Give the same agent another task (reuses login session)
web-agent run "Navigate to settings and export data" --session-id sess-123 --no-wait
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
web-agent run "task" --no-wait

# Explicit configuration
web-agent run "task" \
  --llm gpt-4o \
  --proxy-country gb \
  --keep-alive \
  --no-wait

# With cloud profile (preserves cookies across sessions)
web-agent run "task" --profile <profile-id> --no-wait
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
web-agent run "task" --no-wait
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

### Troubleshooting

**Session reuse fails after `task stop`**:
If you stop a task and try to reuse its session, the new task may get stuck at "created" status. Solution: create a new agent instead.
```bash
# This may fail:
web-agent task stop <task-id>
web-agent run "new task" --session-id <same-session>  # Might get stuck

# Do this instead:
web-agent run "new task" --profile <profile-id>  # Fresh session
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
web-agent sessions                # List active sessions
web-agent close                   # Close current session
web-agent close --all             # Close all sessions
```

### Global Options

| Option | Description |
|--------|-------------|
| `--session NAME` | Named session (default: "default") |
| `--browser MODE` | Browser mode (only if multiple modes installed) |
| `--profile ID` | Cloud profile ID for persistent cookies |
| `--json` | Output as JSON |
| `--api-key KEY` | Override API key |

## Common Patterns

### Test a Local Dev Server with Cloud Browser

```bash
# Start dev server
npm run dev &  # localhost:3000

# Tunnel it
web-agent tunnel 3000
# → url: https://abc.trycloudflare.com

# Browse with cloud browser
web-agent open https://abc.trycloudflare.com
web-agent state
web-agent screenshot
```

### Form Submission

```bash
web-agent open https://example.com/contact
web-agent state
# Shows: [0] input "Name", [1] input "Email", [2] textarea "Message", [3] button "Submit"
web-agent input 0 "John Doe"
web-agent input 1 "john@example.com"
web-agent input 2 "Hello, this is a test message."
web-agent click 3
web-agent state   # Verify success
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

1. **Install with `--remote-only`** for sandboxed environments — no `--browser` flag needed
2. **Always run `state` first** to see available elements and their indices
3. **Sessions persist** across commands — the browser stays open until you close it
4. **Tunnels are independent** — they don't require or create a browser session, and persist across `web-agent close`
5. **Use `--json`** for programmatic parsing
6. **`tunnel` is idempotent** — calling it again for the same port returns the existing URL
7. **Close when done** — `web-agent close` closes the browser; `web-agent tunnel stop --all` stops tunnels

## Troubleshooting

**"Browser mode 'chromium' not installed"?**
- You installed with `--remote-only` which doesn't include local modes
- This is expected behavior for sandboxed agents
- If you need local browser, reinstall with `--full`

**Cloud browser won't start?**
- Verify `web_agent_API_KEY` is set
- Check your API key at https://web-agent.com

**Tunnel not working?**
- Verify cloudflared is installed: `which cloudflared`
- If missing, install manually (see Setup section) or re-run `install.sh --remote-only`
- `web-agent tunnel list` to check active tunnels
- `web-agent tunnel stop <port>` and retry

**Element not found?**
- Run `web-agent state` to see current elements
- `web-agent scroll down` then `web-agent state` — element might be below fold
- Page may have changed — re-run `state` to get fresh indices

## Cleanup

**Close the browser when done:**

```bash
web-agent close              # Close browser session
web-agent tunnel stop --all  # Stop all tunnels (if any)
```

Browser sessions and tunnels are managed separately, so close each as needed.
