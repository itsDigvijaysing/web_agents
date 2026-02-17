# web-agent: Complete System Analysis Report

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [The Agent Orchestration Loop](#3-the-agent-orchestration-loop)
4. [Browser Session Layer](#4-browser-session-layer)
5. [DOM Processing Pipeline](#5-dom-processing-pipeline)
6. [Tools and Action System](#6-tools-and-action-system)
7. [LLM Integration Layer](#7-llm-integration-layer)
8. [Event Bus and Watchdog System](#8-event-bus-and-watchdog-system)
9. [System Prompt Engineering](#9-system-prompt-engineering)
10. [Token and Cost Tracking](#10-token-and-cost-tracking)
11. [Configuration and Environment](#11-configuration-and-environment)
12. [Test Infrastructure](#12-test-infrastructure)
13. [Data Flow: End-to-End Request Lifecycle](#13-data-flow-end-to-end-request-lifecycle)
14. [Roadmap and Future Architecture](#14-roadmap-and-future-architecture)
15. [File Reference Index](#15-file-reference-index)

---

## 1. Executive Summary

web-agent is AI agents to autonomously control web browsers via Chrome DevTools Protocol (CDP). The core innovation is a tight loop between browser state observation (DOM snapshots + screenshots) and LLM-driven action decisions (click, type, scroll, navigate).

The system processes roughly this pipeline per step: capture DOM snapshot via CDP, serialize it into an LLM-friendly text format with indexed interactive elements, send to an LLM along with the task description, parse the structured action response, execute the actions on the browser, and repeat until the task is done or the step budget is exhausted.

Key design decisions:
- Event-driven architecture using the bubus event bus to coordinate loosely-coupled watchdog services
- Service pattern with pydantic v2 models for type-safe configuration and data flow
- Protocol-based LLM abstraction supporting 14+ providers through a unified ainvoke interface
- Multi-target CDP management for handling tabs, iframes, and cross-origin content

---

## 2. System Architecture Overview

The architecture consists of six major subsystems that communicate primarily through events:

**Agent** (orchestrator) drives the step loop, calling into BrowserSession for state and Tools for action execution. The Agent never touches CDP directly.

**BrowserSession** manages the browser lifecycle and coordinates watchdog services. It owns the CDP client connection and all target/session management. It exposes browser operations as events that watchdogs can subscribe to.

**DomService** handles the computationally intensive work of capturing CDP snapshots, building enhanced DOM trees with accessibility information, and serializing them into text representations the LLM can reason about.

**Tools** maintains a registry of available actions (click, type, navigate, etc.) and dispatches LLM-chosen actions to their handlers. Each action handler translates the abstract action into concrete browser events.

**LLM Layer** provides a protocol-based abstraction over 14+ LLM providers, handling structured output parsing, retries, rate limit fallbacks, and token tracking.

**Event Bus** (bubus) connects everything — BrowserSession emits events, watchdogs subscribe and react, and the system stays loosely coupled.

Reference: web_agent/__init__.py (lazy import system for all exports)

---

## 3. The Agent Orchestration Loop

### 3.1 Agent Initialization

The Agent constructor (web_agent/agent/service.py, lines 134-482) accepts the task string and wires together all dependencies. Key initialization steps:

- If no LLM is provided, falls back to the configured default or Chatwebagent
- Flash mode disables planning and strips plan fields from the output schema
- Auto-configures screenshot resize for Claude Sonnet models that have specific vision requirements
- Generates a uuid7 session ID and resolves the browser session (creating one if not provided)
- Sets up the Tools registry, optionally enabling coordinate clicking for models that support it
- Extracts URLs from the task text and converts them into initial navigate actions
- Creates the MessageManager with the appropriate SystemPrompt template

### 3.2 The run() Method — Main Step Loop

The run method (lines 2453-2661) is the top-level entry point with a default budget of 500 steps.

**Setup Phase:** Installs a CTRL+C signal handler for pause/resume/force-exit, dispatches cloud events for session tracking, starts the browser session, registers any skill actions, and executes initial navigation actions.

**Main Loop:** Each iteration of the while loop (line 2535) follows this sequence:
1. Checks for external pause signals and blocks if paused
2. Checks the consecutive failure ceiling (configurable, default 5)
3. Checks the external stop flag
4. Calls the step method wrapped in an asyncio timeout
5. If the step returns "done", breaks the loop

If max_steps is exhausted without completion, the agent logs a budget-exceeded message.

**Teardown:** Logs token usage summary, unregisters signal handlers, emits cloud update events, optionally generates a GIF recording, and closes resources.

### 3.3 The step() Method — Single Step Pipeline

Each step (lines 1016-1040) is a three-phase pipeline:

**Phase 1 — Context Preparation** (via _prepare_context, lines 1042-1115): Captures the current browser state including DOM, screenshot, URL, and tab list. Checks for new downloads. Updates available actions based on current page context. Builds the message array for the LLM including state, history, budget warnings, loop detection nudges, and exploration prompts.

**Phase 2 — LLM Decision** (via _get_next_action, lines 1131-1164): Sends the prepared messages to the LLM with a timeout. The LLM returns a structured AgentOutput containing thinking, evaluation, memory, next goal, and a list of actions.

**Phase 3 — Action Execution** (via _execute_actions and multi_act, lines 1166-1172): Iterates over the action list, executing each through the Tools registry. Two layers of page-change guards prevent executing stale actions after navigation or URL changes.

**Post-Processing** (via _post_process): Updates plan state, runs loop detection, adjusts failure counters, and logs results.

**Error Handling:** All errors are caught by _handle_step_error which increments the failure counter and prepares error context for the next step.

### 3.4 Multi-Action Execution and Guards

The multi_act method (lines 2665-2783) processes action queues with safety guards:

- Actions tagged with terminates_sequence (navigate, go_back, switch_tab) abort remaining queued actions since the page state will change
- A runtime guard compares pre/post URL and focus target after each action, aborting the queue on any change
- The "done" action must appear alone (not combined with other actions)
- A configurable wait_between_actions delay prevents overwhelming the browser

### 3.5 Done Detection

The agent reaches "done" through three mechanisms:

- **Explicit done action:** The LLM emits a done action with success flag and result text
- **Forced done on budget exhaustion:** When approaching max_steps, a system message instructs the LLM to summarize findings and emit done
- **Forced done after max failures:** After hitting the consecutive failure ceiling, the agent forces a done action to preserve partial results

---

## 4. Browser Session Layer

### 4.1 Session Lifecycle

BrowserSession (web_agent/browser/session.py, line 94) manages the complete browser lifecycle through events.

**start()** (line 553): Dispatches a BrowserStartEvent. The event handler (on_BrowserStartEvent, line 604) first attaches all watchdogs, then determines the browser source:
- Cloud browser: Creates a cloud instance via the API and gets a CDP URL
- Local browser: Dispatches BrowserLaunchEvent, which LocalBrowserWatchdog handles to find/launch Chrome and return a CDP URL
- Remote: Uses a pre-configured CDP URL

After obtaining the CDP URL, it calls connect() to establish the CDP WebSocket connection and dispatches BrowserConnectedEvent to notify all watchdogs.

**kill()** (line 560): Saves storage state, dispatches BrowserStopEvent with force=True, stops the event bus, resets all state, and creates a fresh event bus.

**stop()** (line 579): Same as kill but with force=False — gracefully disconnects without terminating the browser process. Useful for reconnection scenarios.

### 4.2 CDP Connection Management

The session maintains a root CDP client for browser-level operations and per-target session IDs for page-level operations. The SessionManager (web_agent/browser/session_manager.py) tracks:
- Target-to-session mappings (each tab/iframe gets a CDP session)
- Page targets vs service worker targets
- The agent's current focus target (which tab the agent is interacting with)

### 4.3 Browser State Collection

get_browser_state_summary() (line 1304) dispatches a BrowserStateRequestEvent. The DOMWatchdog handles this by orchestrating parallel CDP calls to capture:
- DOM snapshot (DOMSnapshot.captureSnapshot)
- Full accessibility tree (Accessibility.getFullAXTree)
- DOM tree (DOM.getDocument)
- Screenshot (Page.captureScreenshot)
- Current URL, tab list, viewport dimensions

Results are bundled into a BrowserStateSummary that the agent uses for LLM context.

### 4.4 Navigation and Tab Management

Navigation (on_NavigateToUrlEvent, line 692) handles both same-tab and new-tab navigation. For new tabs, it creates a CDP target and attaches to it. It handles blank-tab reuse (if already on about:blank, reuses instead of creating another tab).

Tab switching dispatches SwitchTabEvent, and tab closing dispatches CloseTabEvent. The agent tracks its focus target via AgentFocusChangedEvent.

---

## 5. DOM Processing Pipeline

### 5.1 DOM Capture

DomService (web_agent/dom/service.py, line 35) orchestrates DOM capture through three parallel CDP calls per target:
- DOMSnapshot.captureSnapshot — gets the flattened document layout with computed styles
- DOM.getDocument — gets the hierarchical DOM tree
- Accessibility.getFullAXTree — gets the full accessibility tree

These are merged using backend node IDs as join keys to create EnhancedDOMTreeNode objects that combine HTML structure, accessibility properties, and layout information.

### 5.2 Enhanced DOM Tree Construction

get_dom_tree() (line 644) builds the enhanced tree by:
1. Fetching all three CDP trees simultaneously
2. Building a lookup from backend node IDs to accessibility nodes
3. Merging accessibility information (role, name, description, properties) into each DOM node
4. Processing iframes recursively (up to configurable max_iframes and max_iframe_depth)
5. Calculating coordinate offsets for nested iframes
6. Detecting clickable elements through both explicit attributes and JS click listeners

### 5.3 Element Indexing

The serializer assigns sequential integer indexes to all interactive elements. These indexes are the primary mechanism by which the LLM refers to elements — when the LLM says "click element 35", the Tools system looks up index 35 in the selector_map to find the actual DOM node.

The selector_map is a dictionary mapping integer indexes to element metadata (coordinates, target ID, selector, accessibility info). This map is rebuilt on every step since the DOM changes between actions.

### 5.4 Serialization for LLM

DOMTreeSerializer (web_agent/dom/serializer/serializer.py, line 41) converts the enhanced DOM tree into a text format the LLM can reason about. The format uses indentation to represent hierarchy:

Interactive elements appear as indexed entries with their type, attributes, and text content. New elements (those that appeared since the last step) are marked with an asterisk prefix. Non-interactive text content appears without indexes for context.

The serializer applies several optimizations:
- Paint order filtering removes elements hidden behind others
- Viewport threshold filtering limits elements to those near the visible area
- Diff tracking marks new elements that appeared since the last step

### 5.5 ClickableElementDetector

The ClickableElementDetector (web_agent/dom/serializer/clickable_elements.py) determines which elements are interactive through a combination of:
- Semantic HTML tags (button, a, input, select, textarea)
- ARIA roles (button, link, menuitem, tab, etc.)
- Event listener detection (JS click handlers detected via CDP)
- CSS cursor properties
- Accessibility tree role information

---

## 6. Tools and Action System

### 6.1 Action Registry

The Tools class (web_agent/tools/service.py) maintains a Registry (web_agent/tools/registry/service.py, line 32) of available actions. Each action is registered with:
- A name (used in the LLM schema)
- A pydantic model for parameters
- A description for the LLM
- An async handler function
- Metadata flags (terminates_sequence, page_specific, etc.)

### 6.2 Available Actions

The standard action set includes:

**Navigation:** navigate (go to URL, optionally in new tab), go_back (browser back), switch_tab (change active tab), close_tab (close a tab)

**Interaction:** click_element (click by index), input_text (type into indexed element), send_keys (keyboard shortcuts like Enter, Escape, Ctrl+A), select_dropdown_option (select from dropdown by index), upload_file (upload to file input)

**Scrolling:** scroll (up/down/left/right by configurable amount), scroll_to_text (find and scroll to specific text)

**Information Gathering:** extract (use LLM to extract structured data from the full page), read_content (get page text content), search_page (find text patterns on the page), find_elements (query DOM with CSS selectors), screenshot (capture current view)

**Task Management:** done (signal task completion with result text and success flag), get_dropdown_options (list options in a dropdown element)

### 6.3 Action Dispatch

The act() method (line 2167) iterates over the action model fields. For each non-None action, it calls registry.execute_action() which looks up the registered handler and calls it with the parameters and browser session context. Errors are caught and wrapped in ActionResult objects.

### 6.4 Coordinate vs Index-Based Clicking

Two clicking modes exist:
- **Index-based** (default): The LLM specifies an element index from the serialized DOM. The Tools system looks up the element in the selector_map and clicks it via CDP DOM operations.
- **Coordinate-based**: Enabled for models that support it (requires vision). The LLM specifies pixel coordinates directly from the screenshot. Used when DOM indexing is insufficient (e.g., canvas elements, complex SVG).

### 6.5 Sensitive Data Handling

The Tools system supports sensitive data injection. When sensitive_data is provided, placeholder values in LLM actions are replaced with real credentials at execution time. The LLM never sees actual passwords or tokens — it works with placeholder names, and the Tools layer substitutes real values during input_text execution.

---

## 7. LLM Integration Layer

### 7.1 Protocol-Based Abstraction

BaseChatModel (web_agent/llm/base.py, line 18) is a Python Protocol defining the interface all LLM providers must implement:
- model: str — the model identifier
- provider, name, model_name — metadata properties
- ainvoke() — the async invocation method with optional structured output

The protocol uses overloads: when output_format is None, ainvoke returns a string completion. When a pydantic model type is provided, it returns a parsed instance of that type.

### 7.2 Supported Providers

The library ships with 14+ provider implementations:

- ChatGoogle (web_agent/llm/google/chat.py) — Gemini models via google-genai SDK
- ChatOpenAI (web_agent/llm/openai/chat.py) — GPT models via openai SDK
- ChatAnthropic (web_agent/llm/anthropic/chat.py) — Claude models via anthropic SDK
- ChatGroq (web_agent/llm/groq/chat.py) — Fast inference models
- ChatOllama (web_agent/llm/ollama/chat.py) — Local models via Ollama
- ChatAzureOpenAI (web_agent/llm/azure/chat.py) — Azure-hosted OpenAI models
- ChatAWSBedrock (web_agent/llm/aws/chat_bedrock.py) — AWS Bedrock models
- ChatAnthropicBedrock (web_agent/llm/aws/chat_anthropic.py) — Claude on Bedrock
- ChatDeepSeek (web_agent/llm/deepseek/chat.py) — DeepSeek models
- ChatMistral (web_agent/llm/mistral/chat.py) — Mistral models
- ChatCerebras (web_agent/llm/cerebras/chat.py) — Cerebras inference
- ChatOpenRouter (web_agent/llm/openrouter/chat.py) — OpenRouter aggregator
- ChatVercel (web_agent/llm/vercel/chat.py) — Vercel AI SDK
- ChatOCIRaw (web_agent/llm/oci_raw/chat.py) — Oracle Cloud models
- Chatwebagent (web_agent/llm/web_agent/chat.py) — The hosted web-agent service

### 7.3 Structured Output and Retry Logic

Each provider implements structured output differently:
- OpenAI/Azure use response_format with JSON schema
- Google Gemini uses response_schema generation config
- Anthropic uses tool_use with a single-tool pattern
- Others fall back to JSON instruction in the system prompt with post-parsing

The retry logic (in get_model_output, lines 1924-1933) handles:
- Rate limits (ModelRateLimitError) — switches to fallback_llm if configured
- Provider errors (ModelProviderError) — same fallback mechanism
- Validation errors — re-raised to the caller
- Empty responses — retried once with a clarification message, then synthesizes a noop done action

### 7.4 Message Management

MessageManager (web_agent/agent/message_manager/) maintains the conversation history sent to the LLM. It handles:
- System prompt selection based on model provider and flash mode
- State message construction with DOM tree, screenshot, and metadata
- History compaction when the message array exceeds token limits
- Injection of system nudges (budget warnings, loop detection, exploration prompts)

---

## 8. Event Bus and Watchdog System

### 8.1 Event Bus Architecture

The bubus EventBus is the communication backbone. Events are pydantic models that extend BaseEvent with typed result parameters. Handlers register for specific event types and can return results or raise errors. Events support:
- Synchronous dispatch (fire and continue)
- Awaitable dispatch (wait for all handlers to complete)
- Result collection (get typed results from handlers)
- Timeout enforcement per handler

### 8.2 Event Flow

The major event categories are:

**Lifecycle Events:** BrowserStartEvent, BrowserStopEvent, BrowserLaunchEvent, BrowserConnectedEvent, BrowserStoppedEvent, BrowserKillEvent

**Interaction Events:** NavigateToUrlEvent, ClickElementEvent, ClickCoordinateEvent, TypeTextEvent, SendKeysEvent, ScrollEvent, ScrollToTextEvent, SwitchTabEvent, CloseTabEvent, GoBackEvent, GoForwardEvent, RefreshEvent, WaitEvent, UploadFileEvent

**State Events:** BrowserStateRequestEvent, ScreenshotEvent, GetDropdownOptionsEvent, ElementSelectedEvent, AgentFocusChangedEvent

**Tab Events:** TabCreatedEvent, TabClosedEvent

**Error Events:** TargetCrashedEvent, BrowserErrorEvent (not in events.py but used internally)

### 8.3 Watchdog Services

Each watchdog is a BaseWatchdog subclass (web_agent/browser/watchdog_base.py, line 14) that subscribes to relevant events and manages an isolated aspect of browser state:

**LocalBrowserWatchdog** (local_browser_watchdog.py): Handles browser process lifecycle — finding the browser executable, launching Chrome with the correct arguments, waiting for CDP to become ready, managing process cleanup and zombie prevention.

**DOMWatchdog** (dom_watchdog.py): Handles BrowserStateRequestEvent by orchestrating the DomService to capture DOM snapshots, build accessibility trees, serialize the DOM, and capture screenshots. This is the most performance-critical watchdog.

**ScreenshotWatchdog** (screenshot_watchdog.py): Handles ScreenshotEvent by capturing and processing browser screenshots. Manages screenshot caching and resize operations.

**DownloadsWatchdog** (downloads_watchdog.py): Monitors CDP download events. Handles automatic PDF downloads, tracks download progress, manages download directories, and makes downloaded files available to the agent.

**PopupsWatchdog** (popups_watchdog.py): Monitors JavaScript dialogs (alert, confirm, prompt) and automatically handles them. Prevents dialogs from blocking the agent's actions.

**SecurityWatchdog** (security_watchdog.py): Enforces domain restrictions and navigation policies. Can whitelist/blacklist domains. Blocks navigation to restricted URLs. Monitors for security-relevant CDP events.

**AboutBlankWatchdog** (aboutblank_watchdog.py): Detects when the browser lands on about:blank or empty pages and handles redirects appropriately to prevent the agent from getting stuck.

**DefaultActionWatchdog** (default_action_watchdog.py): Handles core browser interactions (click, type, scroll, navigation) by translating high-level events into CDP commands. This is the primary action executor.

**PermissionsWatchdog** (permissions_watchdog.py): Manages browser permission requests (camera, microphone, geolocation, notifications) by automatically granting or denying based on configuration.

**StorageStateWatchdog** (storage_state_watchdog.py): Manages cookie and localStorage persistence. Saves and restores browser state between sessions using the storage_state configuration.

**RecordingWatchdog** (recording_watchdog.py): Captures step-by-step screenshots for GIF generation. Tracks the agent's visual progress through the task.

**HarRecordingWatchdog** (har_recording_watchdog.py): Records HTTP Archive (HAR) files of all network requests during the session. Useful for debugging and replay.

**CrashWatchdog** (crash_watchdog.py): Monitors for browser crashes via TargetCrashedEvent and handles recovery or graceful failure reporting.

---

## 9. System Prompt Engineering

### 9.1 Prompt Templates

The system uses multiple prompt variants stored as markdown files (web_agent/agent/system_prompts/):

- system_prompt.md — Full prompt with thinking, planning, and detailed browser rules
- system_prompt_flash.md — Compact prompt for flash mode (no planning, reduced instructions)
- system_prompt_anthropic_flash.md — Anthropic-specific flash variant
- system_prompt_no_thinking.md — Variant without the thinking/evaluation fields
- system_prompt_web_agent.md — Variant for the hosted web-agent service

### 9.2 Prompt Structure

The full system prompt (system_prompt.md) is structured into tagged sections:

**intro** — Defines the agent's capabilities (navigation, form filling, extraction, file management, agent loop operation)

**input** — Describes the five input channels: agent_history (previous actions and results), agent_state (task, file system, todos, step info), browser_state (URL, tabs, indexed elements), browser_vision (screenshot with bounding boxes), read_state (extraction results, shown only when relevant)

**browser_state format** — Elements appear as indexed entries where the index is the interaction handle. Indentation represents HTML hierarchy. Starred elements (asterisk prefix) are new since the last step.

**browser_rules** — 20+ rules governing browser interaction: only interact with indexed elements, handle popups immediately, use search_page before scrolling, detect and break loops, handle CAPTCHAs with limited retry, use filters before browsing, handle autocomplete/combobox fields properly.

**file_system** — Instructions for persistent file management including todo.md tracking and results.md accumulation for long tasks.

**planning** — Adaptive planning rules: skip planning for simple tasks, plan immediately for complex-but-clear tasks, explore first for unclear tasks. Plan items use status markers for tracking.

**task_completion_rules** — When and how to call the done action, including partial result handling, format requirements, budget awareness, and the rule that done must appear as a sole action.

### 9.3 Dynamic Injections

Beyond the static prompt, the agent injects dynamic content per step:

- **Budget warnings** at 75% and 90% of max_steps
- **Loop detection nudges** when the agent repeats similar actions
- **Exploration nudges** when the agent hasn't formed a plan after several steps
- **Replan nudges** when the current plan seems stalled
- **Force-done messages** on the final step or after max failures

---

## 10. Token and Cost Tracking

The token tracking system (web_agent/tokens/service.py) wraps LLM ainvoke calls with a tracked_ainvoke proxy (line 339). This interceptor:

- Records input and output token counts from each LLM response
- Maps token counts to costs using provider-specific pricing (web_agent/tokens/mappings.py)
- Supports custom pricing overrides (web_agent/tokens/custom_pricing.py)
- Aggregates totals across all steps for the run() summary
- Reports cost breakdowns by model in the final log output

Token usage is returned in ChatInvokeUsage objects (web_agent/llm/views.py, line 8) alongside each completion, containing input_tokens, output_tokens, and optional cache/reasoning breakdowns.

---

## 11. Configuration and Environment

### 11.1 Configuration System

The Config class (web_agent/config.py) provides a unified interface combining:
- Environment variables via pydantic-settings (FlatEnvConfig)
- Legacy lazy-loading config (OldConfig) for backward compatibility
- A singleton CONFIG instance used throughout the codebase

### 11.2 BrowserProfile

BrowserProfile (web_agent/browser/profile.py) is the central configuration model for browser behavior. Key settings include:
- executable_path — custom Chrome binary location
- headless — run without visible window
- user_data_dir — persistent browser profile directory
- channel — browser channel (chromium, chrome, edge, brave)
- enable_default_extensions — uBlock Origin, cookie handler, etc.
- security settings — allowed/blocked domains, disable_security flag
- display configuration — viewport size, device scale factor
- proxy settings — server, credentials, bypass rules
- CDP-specific settings — extra launch arguments, debugging options

BrowserProfile auto-detects display configuration via detect_display_configuration() which uses AppKit on macOS and screeninfo on Linux/Windows.

### 11.3 Environment Variables

Key environment variables (defined in .env.example):
- GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY — LLM provider keys
- web_agent_EXECUTABLE_PATH — Chrome binary path
- web_agent_HEADLESS — headless mode toggle
- web_agent_LOGGING_LEVEL — log verbosity
- ANONYMIZED_TELEMETRY — opt-in/out of PostHog analytics
- web_agent_API_KEY — cloud service API key

---

## 12. Test Infrastructure

### 12.1 Test Organization

Tests live in tests/ci/ with subdirectories for browser/, interactions/, models/, infrastructure/, and security/. The CI suite contains 656+ tests that run on every commit.

### 12.2 Test Fixtures

The conftest (tests/ci/conftest.py) provides:
- setup_test_environment (autouse) — disables real APIs, sets telemetry off, configures placeholder URLs
- create_mock_llm(actions) — creates an AsyncMock LLM that returns specified JSON action sequences, then defaults to a done action
- browser_session (module-scoped) — a real headless browser session shared across tests in a module
- mock_llm (function-scoped) — default mock that returns done immediately
- event_collector — helper for capturing and filtering events during tests

### 12.3 Test Principles

- Never mock anything except LLMs — all browser operations use real browsers
- Use pytest-httpserver for all test HTML — never hit real remote URLs
- Modern pytest-asyncio — no decorators needed, auto mode enabled
- 120-second timeout per test, 300-second for slow tests
- Module-scoped browser sessions to amortize launch cost

---

## 13. Data Flow: End-to-End Request Lifecycle

This section traces a single request from user input to final result.

**Step 0 — Initialization:** User creates an Agent with a task string and LLM. Agent extracts any URL from the task and prepares an initial navigate action. Browser session is started, which launches Chrome via LocalBrowserWatchdog and establishes a CDP connection.

**Step 1 — Initial Navigation:** The initial_actions execute, navigating to the extracted URL. The browser loads the page.

**Step 2..N — Action Loop:** Each step proceeds as:

1. BrowserSession dispatches BrowserStateRequestEvent
2. DOMWatchdog handles the event by calling DomService.get_serialized_dom_tree()
3. DomService makes three parallel CDP calls: DOMSnapshot.captureSnapshot, DOM.getDocument, Accessibility.getFullAXTree
4. Results are merged into an EnhancedDOMTreeNode tree
5. DOMTreeSerializer converts the tree to indexed text format, building a selector_map
6. ScreenshotWatchdog captures a PNG screenshot via Page.captureScreenshot
7. BrowserStateSummary is returned to the Agent
8. MessageManager builds the LLM message array with system prompt, history, DOM state, and screenshot
9. Agent calls LLM.ainvoke() with the messages and AgentOutput as output_format
10. LLM returns structured JSON with thinking, evaluation, memory, next_goal, and actions
11. Agent validates the response and truncates actions to max_actions_per_step
12. multi_act() iterates over actions, dispatching each as a browser event
13. DefaultActionWatchdog executes the CDP commands (click coordinates, dispatch key events, navigate)
14. Page-change guards check if URL or focus changed, aborting remaining actions if so
15. Results are recorded in history, step counter increments

**Final Step — Completion:** When the LLM emits a done action, the agent extracts the result text, optionally runs a judge to verify quality, fires the done callback, and returns the AgentHistoryList to the caller.

---

## 14. Roadmap and Future Architecture

### 14.1 Vision Pipeline Optimization

The current screenshot capture and processing pipeline runs synchronously within each step. Planned optimizations include parallel screenshot capture during DOM processing, adaptive resolution based on page complexity, and incremental visual diff to reduce token costs for screenshots that haven't changed significantly.

### 14.2 RAG-Based Navigation

For complex workflows like flight booking or multi-step form filling, the planned RAG system will provide pre-defined reference documents that the LLM can query during navigation. These documents will encode domain-specific patterns (airline booking flows, form field mappings, common UI patterns) allowing the agent to follow established procedures rather than exploring from scratch each time.

### 14.3 mem0-Inspired Context System

Drawing from the mem0 paper on persistent memory for AI agents, the planned context system will implement:
- Cross-session memory persistence for frequently visited sites
- Pattern recognition for common page layouts and interaction sequences
- Hierarchical memory with working memory (current step), episodic memory (current session), and semantic memory (cross-session patterns)
- Memory consolidation to compress and deduplicate stored experiences

---

## 15. File Reference Index

### Core Services
| File | Lines | Description |
|------|-------|-------------|
| web_agent/agent/service.py | ~4076 | Agent orchestrator — step loop, LLM interaction, action execution |
| web_agent/browser/session.py | ~3552 | Browser lifecycle, CDP connections, tab management, state collection |
| web_agent/tools/service.py | ~2595 | Action registry, action dispatch, sensitive data handling |
| web_agent/dom/service.py | ~1134 | DOM snapshot capture, accessibility tree, enhanced tree construction |

### Browser Layer
| File | Description |
|------|-------------|
| web_agent/browser/profile.py | BrowserProfile configuration, Chrome launch args, display detection |
| web_agent/browser/session_manager.py | Target-to-session mapping, tab tracking |
| web_agent/browser/watchdog_base.py | BaseWatchdog class — event handler auto-registration |
| web_agent/browser/events.py | All event definitions (30+ event types) |
| web_agent/browser/demo_mode.py | Visual overlay for demonstrations |
| web_agent/browser/video_recorder.py | Step recording for GIF generation |

### Watchdogs
| File | Description |
|------|-------------|
| web_agent/browser/watchdogs/local_browser_watchdog.py | Browser launch, process management, CDP readiness |
| web_agent/browser/watchdogs/dom_watchdog.py | DOM state orchestration, snapshot coordination |
| web_agent/browser/watchdogs/screenshot_watchdog.py | Screenshot capture and caching |
| web_agent/browser/watchdogs/downloads_watchdog.py | File download handling, PDF auto-download |
| web_agent/browser/watchdogs/popups_watchdog.py | JavaScript dialog management |
| web_agent/browser/watchdogs/security_watchdog.py | Domain restrictions, navigation policies |
| web_agent/browser/watchdogs/default_action_watchdog.py | Core action execution (click, type, scroll) |
| web_agent/browser/watchdogs/aboutblank_watchdog.py | Empty page detection and redirect |
| web_agent/browser/watchdogs/permissions_watchdog.py | Browser permission auto-handling |
| web_agent/browser/watchdogs/storage_state_watchdog.py | Cookie and localStorage persistence |
| web_agent/browser/watchdogs/recording_watchdog.py | Step screenshot capture for recordings |
| web_agent/browser/watchdogs/har_recording_watchdog.py | HTTP Archive recording |
| web_agent/browser/watchdogs/crash_watchdog.py | Browser crash detection and recovery |

### DOM Processing
| File | Description |
|------|-------------|
| web_agent/dom/serializer/serializer.py | DOMTreeSerializer — converts DOM to indexed text |
| web_agent/dom/serializer/clickable_elements.py | Interactive element detection |
| web_agent/dom/serializer/html_serializer.py | HTML-format serialization variant |
| web_agent/dom/serializer/paint_order.py | Paint order filtering for hidden elements |
| web_agent/dom/enhanced_snapshot.py | CDP snapshot lookup and merging |
| web_agent/dom/views.py | EnhancedDOMTreeNode, SerializedDOMState models |

### LLM Providers
| File | Provider |
|------|----------|
| web_agent/llm/base.py | BaseChatModel protocol definition |
| web_agent/llm/google/chat.py | Google Gemini (ChatGoogle) |
| web_agent/llm/openai/chat.py | OpenAI GPT (ChatOpenAI) |
| web_agent/llm/anthropic/chat.py | Anthropic Claude (ChatAnthropic) |
| web_agent/llm/groq/chat.py | Groq (ChatGroq) |
| web_agent/llm/ollama/chat.py | Ollama local models (ChatOllama) |
| web_agent/llm/azure/chat.py | Azure OpenAI (ChatAzureOpenAI) |
| web_agent/llm/aws/chat_bedrock.py | AWS Bedrock (ChatAWSBedrock) |
| web_agent/llm/deepseek/chat.py | DeepSeek (ChatDeepSeek) |
| web_agent/llm/mistral/chat.py | Mistral (ChatMistral) |
| web_agent/llm/web_agent/chat.py | Hosted service (Chatwebagent) |
| web_agent/llm/views.py | ChatInvokeCompletion, ChatInvokeUsage models |

### Configuration and Infrastructure
| File | Description |
|------|-------------|
| web_agent/config.py | Unified config — env vars, pydantic settings, singleton |
| web_agent/tokens/service.py | Token tracking, cost calculation, ainvoke wrapping |
| web_agent/tokens/mappings.py | Per-model token pricing data |
| web_agent/logging_config.py | Centralized logging configuration |
| web_agent/telemetry/service.py | PostHog analytics integration |
| web_agent/mcp/server.py | MCP server mode for Claude Desktop |
| web_agent/mcp/client.py | MCP client for connecting external tools |

### Agent Internals
| File | Description |
|------|-------------|
| web_agent/agent/views.py | AgentOutput, ActionModel, AgentHistoryList, AgentState |
| web_agent/agent/message_manager/ | Message array construction, history compaction |
| web_agent/agent/system_prompts/ | System prompt templates (8 variants) |
| web_agent/agent/cloud_events.py | Cloud sync event definitions |

### Tools
| File | Description |
|------|-------------|
| web_agent/tools/views.py | Action pydantic models (ClickElementAction, NavigateAction, etc.) |
| web_agent/tools/registry/service.py | Registry class — action registration and dispatch |
| web_agent/tools/registry/views.py | Registry entry metadata |
| web_agent/tools/extraction/ | Page content extraction utilities |
