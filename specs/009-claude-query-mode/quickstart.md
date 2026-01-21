# Quickstart: Claude Query Mode

**Feature**: 009-claude-query-mode
**Date**: 2026-01-21

## Prerequisites

1. **Claude Max subscription** with API access
2. **Ara voice assistant** running with MongoDB
3. **Internet connectivity** for Claude queries

## Setup

### 1. Get Your Anthropic API Key

1. Log in to your Anthropic account at https://console.anthropic.com/
2. Navigate to API Keys section
3. Create a new API key or use existing one
4. Copy the key (starts with `sk-ant-`)

### 2. Configure Ara

Add your API key to the environment:

```bash
# Option A: Add to shell profile (~/.bashrc or ~/.zshrc)
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Option B: Add to Ara config file (~/.ara/config.yaml)
# claude:
#   api_key: "sk-ant-your-key-here"
```

### 3. Verify Setup

```bash
# Test API key is set
echo $ANTHROPIC_API_KEY

# Start Ara
cd /path/to/ara
python -m ara
```

## Voice Commands

### Basic Queries

| Command | Description |
|---------|-------------|
| "Ask Claude what is quantum computing" | Send a question to Claude |
| "Ask Claude to explain photosynthesis" | Request an explanation |
| "Hey Claude, what's the weather like in Paris?" | Alternative trigger phrase |

### Follow-up Conversations

After Claude responds, you have 5 seconds to ask follow-ups without the trigger:

```
You: "Ask Claude what is machine learning"
Ara: [Claude's explanation...]
You: "Can you give me an example?" ← No "ask Claude" needed
Ara: [Follow-up response...]
You: "What about deep learning?" ← Still in conversation
Ara: [Another response...]
```

### Session Management

| Command | Description |
|---------|-------------|
| "New conversation" | Clear history, start fresh |
| "Start over" | Same as "new conversation" |

### History Summarization

| Command | Description |
|---------|-------------|
| "Summarize my Claude conversations today" | Summary of today's queries |
| "What are the key learnings from Claude this week" | Weekly insights |
| "Summarize my Claude queries this month" | Monthly summary |

## Audio Feedback

| Sound | Meaning |
|-------|---------|
| Musical loop | Waiting for Claude's response |
| Loop stops | Response is about to be spoken |
| Error tone | Something went wrong |

## Error Messages

| Message | Meaning | Action |
|---------|---------|--------|
| "Internet is unavailable" | No connectivity | Check network connection |
| "Claude is taking longer than expected, try again?" | 30-second timeout | Say "yes" to retry |
| "Please set up your Claude authentication" | No API key | Configure API key |
| "Claude service is unavailable" | API error | Try again later |

## Tips

1. **Be specific**: Claude gives better answers to specific questions
2. **Use follow-ups**: Build on previous responses for deeper exploration
3. **Keep it conversational**: Claude understands natural language
4. **Say "new conversation"**: When switching topics completely
5. **Review summaries**: Check weekly summaries for insights you might have forgotten

## Troubleshooting

### "Please set up authentication"

Your API key isn't configured. Set the `ANTHROPIC_API_KEY` environment variable.

### "Internet is unavailable"

1. Check your network connection
2. Try `ping api.anthropic.com` from terminal
3. Verify firewall isn't blocking HTTPS

### "Claude is taking longer..."

1. Claude API might be under load
2. Say "yes" to retry
3. If persistent, check status.anthropic.com

### No response after "ask Claude"

1. Ensure you completed the trigger phrase ("ask Claude" + your question)
2. Speak clearly and wait for the waiting indicator
3. Check Ara logs for errors: `tail -f ~/.ara/logs/ara.log`

## Development Testing

```bash
# Run unit tests
PYTHONPATH=src python -m pytest tests/unit/test_claude*.py -v

# Run integration tests (requires API key)
PYTHONPATH=src python -m pytest tests/integration/test_claude_flow.py -v

# Test intent recognition
python -c "
from ara.router.intent import IntentClassifier
classifier = IntentClassifier()
result = classifier.classify('ask Claude what is AI')
print(f'Intent: {result.type}, Query: {result.entities.get(\"query\")}')
"
```
