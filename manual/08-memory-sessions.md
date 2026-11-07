# 8. Memory & Sessions

HackBot automatically manages conversation memory, session persistence, and context summarization.

---

## Auto-Save

Sessions are saved automatically:
- **Chat mode**: After every exchange (user message + AI response)
- **Agent mode**: After each step (with findings and tool history)
- **Plan mode**: After plan generation

Auto-save is non-blocking — failures don't interrupt your session.

---

## Session Management

### Save a Session
```
/save                         # Save with auto-generated name
/save my_assessment           # Save with custom name
```

### Load a Session
```
/load                         # List available sessions
/load my_assessment           # Load by name
/load chat_1707984000000      # Load by ID
```

### List Sessions
```
/sessions                     # List all sessions (up to 25)
/sessions chat                # Filter by chat mode
/sessions agent               # Filter by agent mode
/sessions plan                # Filter by plan mode
```

### Clear / Reset
```
/clear                        # Clear current conversation history
/reset                        # Reset HackBot completely (all modes)
```

### GUI
Use the **Sessions** panel to browse, restore, or delete saved sessions.

---

## Session Storage

Sessions are saved as JSON files in:
```
~/.local/share/hackbot/sessions/
```

Each session contains:
| Field | Description |
|-------|-------------|
| `id` | Unique ID (format: `{mode}_{timestamp_ms}`) |
| `mode` | `chat`, `agent`, or `plan` |
| `name` | User-provided or auto-generated name |
| `created` | When the session was started |
| `updated` | When the session was last modified |
| `message_count` | Number of messages |
| `target` | Assessment target (agent/plan mode) |
| `summary` | Brief summary of the session |
| `messages` | Full conversation history (system messages filtered out) |

---

## Continue Truncated Responses

If an AI response gets cut off (hits token limit), use:

```
/continue
```

This works in all 3 modes (Chat, Agent, Plan). The AI resumes exactly where it left off.

### How it detects truncation
- Mid-word endings
- Unclosed code blocks
- Incomplete sentences
- Missing closing markers

### GUI
A "Continue" button appears automatically when truncation is detected.

---

## Conversation Summarization

When conversations get very long, HackBot automatically summarizes older messages to stay within the AI's context window.

### How it works
1. When messages exceed the threshold, older messages are selected for summarization
2. The AI generates a structured summary preserving key information
3. The summary replaces the old messages in the conversation
4. Recent messages are kept intact after the summary

### Thresholds

| Mode | Max Messages | Keeps Recent |
|------|-------------|-------------|
| **Chat** | 40 | Last 10 messages |
| **Agent** | 20 | Last 6 messages |

Agent mode has a lower threshold because tool outputs can be very large.

### What the summary preserves
- Findings discovered so far
- Tools executed and their results
- Current assessment state
- IPs, URLs, credentials found
- What's been planned vs. completed

### Fallback
If AI summarization fails (no API key, network error), a plain text placeholder is used instead.

---

## Session Search

Sessions can be found by:
- **Name** — the custom name you gave it
- **Target** — the IP/domain that was assessed
- **Summary** — content within the session summary

Sessions are sorted by `updated` timestamp (newest first) and limited to 50 by default.

---

Next: [Configuration →](09-configuration.md)
