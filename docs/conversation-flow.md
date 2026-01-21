# Ara Conversation Flow

This document describes the complete conversation flow logic in Ara Voice Assistant.

## High-Level Flow

![Conversation Flow Diagram](conversation-flow.png)

```mermaid
flowchart TD
    START([1. Start]) --> LISTEN[2. Listen for Wake Word]
    LISTEN --> |Wake word detected| BEEP1[3. Play wake beep]
    BEEP1 --> RECORD[4. Record user speech]
    RECORD --> |No speech| LISTEN
    RECORD --> |Speech detected| TRANSCRIBE[5. Transcribe audio]
    TRANSCRIBE --> |Empty| LISTEN
    TRANSCRIBE --> CLEAN[6. Clean transcript]
    CLEAN --> CLASSIFY{7. Classify intent}

    CLASSIFY --> |7a: Note/Remember| NOTE_HANDLER[Note Handler]
    CLASSIFY --> |7b: Ask Claude| CLAUDE_HANDLER[Claude Handler]
    CLASSIFY --> |7c: Search/Google| WEB_HANDLER[Tavily Search]
    CLASSIFY --> |7d: Ask Perplexity| PERPLEXITY_HANDLER[Perplexity Search]
    CLASSIFY --> |7z: Other| QUERY_ROUTER[QueryRouter]

    NOTE_HANDLER --> SYNTHESIZE[8. Synthesize response]
    CLAUDE_HANDLER --> SYNTHESIZE
    WEB_HANDLER --> SYNTHESIZE
    PERPLEXITY_HANDLER --> SYNTHESIZE
    QUERY_ROUTER --> SYNTHESIZE

    SYNTHESIZE --> PLAY[9. Play response audio]

    PLAY --> NOTE_CHECK{10. Note mode?}
    NOTE_CHECK --> |Yes| LISTEN
    NOTE_CHECK --> |No| ANYTHING_ELSE[11. Ask Anything else?]

    ANYTHING_ELSE --> AE_LISTEN[12. Listen for response]
    AE_LISTEN --> |No response/silence| GOODBYE[19. Say goodbye]
    AE_LISTEN --> |Response detected| AE_TRANSCRIBE[13. Transcribe response]

    AE_TRANSCRIBE --> AE_CHECK{14. User response}
    AE_CHECK --> |No/Thanks/negative| GOODBYE
    AE_CHECK --> |Yes/affirmative only| PROMPT[15. Ask What else?]
    AE_CHECK --> |Contains question| PROCESS_FOLLOWUP[16. Process question]

    PROMPT --> PROMPT_LISTEN[15a. Listen for question]
    PROMPT_LISTEN --> |No response| GOODBYE
    PROMPT_LISTEN --> |Question received| PROCESS_FOLLOWUP

    PROCESS_FOLLOWUP --> CLASSIFY_FOLLOWUP[17. Classify follow-up intent]
    CLASSIFY_FOLLOWUP --> CLAUDE_CHECK{18. Previous was Claude?}

    CLAUDE_CHECK --> |Yes and general question| ROUTE_CLAUDE[18a. Route to Claude]
    CLAUDE_CHECK --> |No or specific intent| HANDLE_FOLLOWUP[18b. Handle intent normally]

    ROUTE_CLAUDE --> SYNTH_FOLLOWUP[18c. Synthesize response]
    HANDLE_FOLLOWUP --> SYNTH_FOLLOWUP

    SYNTH_FOLLOWUP --> PLAY_FOLLOWUP[18d. Play response]
    PLAY_FOLLOWUP --> ANYTHING_ELSE

    GOODBYE --> LISTEN
```

### Node Reference

| Node | Description |
|------|-------------|
| 1 | Start - Entry point |
| 2 | Listen for Wake Word - Awaiting "Hey Ara" |
| 3 | Play wake beep - Audio feedback |
| 4 | Record user speech - Capture audio |
| 5 | Transcribe audio - Speech-to-text |
| 6 | Clean transcript - Remove filler words |
| 7 | Classify intent - Route based on voice phrase |
| 7a | Note Handler - "Note that...", "Remember..." |
| 7b | Claude Handler - "Ask Claude...", "Hey Claude..." |
| 7c | Tavily Search - "Search for...", "Google..." |
| 7d | Perplexity Search - "Ask Perplexity..." |
| 7z | QueryRouter - Smart routing for other queries |
| 8 | Synthesize response - Generate TTS audio |
| 9 | Play response audio - Speak response |
| 10 | Note mode? - Check for continuation |
| 11 | Ask "Anything else?" - Prompt for follow-up |
| 12 | Listen for response - Wait for user reply |
| 13 | Transcribe response - Convert reply to text |
| 14 | User response - Decision point |
| 15 | Ask "What else?" - Prompt for question |
| 15a | Listen for question - Wait for follow-up |
| 16 | Process question - Handle follow-up |
| 17 | Classify follow-up intent - Categorize |
| 18 | Previous was Claude? - Check conversation context |
| 18a | Route to Claude - Continue Claude conversation |
| 18b | Handle intent normally - Standard processing |
| 18c | Synthesize response - Generate follow-up TTS |
| 18d | Play response - Speak follow-up |
| 19 | Say goodbye - End interaction |
| 22 | Say goodbye - End interaction |

## Detailed Intent Classification (Step 7 Routing)

```mermaid
flowchart TD
    TRANSCRIPT[User transcript] --> INTENT_CLASS{Intent type?}

    INTENT_CLASS --> |7a: Note/Remember| NOTE_CAPTURE[NOTE_CAPTURE]
    INTENT_CLASS --> |7b: Ask Claude| CLAUDE_QUERY[CLAUDE_QUERY]
    INTENT_CLASS --> |7c: Search/Google| WEB_SEARCH[WEB_SEARCH]
    INTENT_CLASS --> |7d: Ask Perplexity| PERPLEXITY[PERPLEXITY_SEARCH]
    INTENT_CLASS --> |Set timer for| TIMER_SET[TIMER_SET]
    INTENT_CLASS --> |Remind me to| REMINDER_SET[REMINDER_SET]
    INTENT_CLASS --> |What time/How long| TIME_QUERY[TIME_QUERY]
    INTENT_CLASS --> |Stop/Cancel| STOP[STOP]
    INTENT_CLASS --> |7z: Other| GENERAL[GENERAL - QueryRouter]

    NOTE_CAPTURE --> NOTE_HANDLER[Note Handler]
    CLAUDE_QUERY --> CLAUDE_HANDLER[Claude Handler]
    WEB_SEARCH --> SEARCH_HANDLER[Tavily Search]
    PERPLEXITY --> PERPLEXITY_HANDLER[Perplexity Search]
    TIMER_SET --> TIMER_HANDLER[Timer Handler]
    REMINDER_SET --> REMINDER_HANDLER[Reminder Handler]
    TIME_QUERY --> TIME_HANDLER[Time Query Handler]
    STOP --> STOP_HANDLER[Stop Handler]
    GENERAL --> QUERY_ROUTER{QueryRouter}

    QUERY_ROUTER --> |Personal data| MONGODB[MongoDB]
    QUERY_ROUTER --> |Factual/current| TAVILY[Tavily Web Search]
    QUERY_ROUTER --> |General knowledge| OLLAMA[Ollama LLM]
```

### Step 7 Query Routing Reference

| Route | Trigger Phrases | Handler |
|-------|-----------------|---------|
| 7a Note | "note that...", "remember...", "add to action items" | MongoDB notes |
| 7b Claude | "ask Claude...", "hey Claude..." | Claude API |
| 7c Web Search | "search for...", "google...", "what's the weather..." | Tavily API |
| 7d Perplexity | "ask Perplexity...", "search with Perplexity..." | Perplexity API |
| 7z Default | Everything else | QueryRouter → MongoDB/Tavily/Ollama |

## Interrupt Handling Flow

```mermaid
flowchart TD
    PLAYING[Playing response audio] --> MONITOR{Monitor for speech}

    MONITOR --> |No speech| COMPLETE[Playback complete]
    MONITOR --> |Speech detected| INTERRUPT[Interrupt detected]

    INTERRUPT --> INT_TRANSCRIBE[Transcribe interrupt]
    INT_TRANSCRIBE --> INT_CHECK{Interrupt type?}

    INT_CHECK --> |Stop| STOP_NOW[Stop immediately, say OK]
    INT_CHECK --> |Wait/Hold on| WAIT_MODE[Enter wait mode]
    INT_CHECK --> |Follow-up question| FOLLOWUP[Process as follow-up]
    INT_CHECK --> |Noise/unclear| RESUME[Resume playback]

    WAIT_MODE --> WAIT_LISTEN[Listen for context]
    WAIT_LISTEN --> COMBINE[Combine with original request]
    COMBINE --> REPROCESS[Reprocess combined request]

    FOLLOWUP --> COMBINE

    STOP_NOW --> END_INT[End interaction]
    RESUME --> PLAYING
    REPROCESS --> NEW_RESPONSE[Generate new response]
```

## "Anything Else?" Decision Logic

```mermaid
flowchart TD
    ASK[Ara: Anything else?] --> LISTEN[Listen 5 seconds]

    LISTEN --> |Timeout/silence| DECLINE[User declined]
    LISTEN --> |Speech detected| TRANSCRIBE[Transcribe]

    TRANSCRIBE --> ANALYZE{Analyze response}

    ANALYZE --> |no/nope/thanks/done| DECLINE
    ANALYZE --> |yes/yeah/sure/okay| AFFIRM{Short response?}
    ANALYZE --> |Contains actual question| QUESTION[Has question]

    AFFIRM --> |3 words or less| PROMPT[Ara: What else?]
    AFFIRM --> |More than 3 words| QUESTION

    PROMPT --> LISTEN2[Listen 10 seconds]
    LISTEN2 --> |No response| DECLINE
    LISTEN2 --> |Question received| QUESTION

    QUESTION --> PROCESS[Process the question]

    DECLINE --> GOODBYE[Ara: Let me know if you need anything]
    GOODBYE --> END([Return to wake word])

    PROCESS --> CLAUDE_CHECK{Previous was<br>Claude intent?}

    CLAUDE_CHECK --> |Yes & general Q| ROUTE_CLAUDE[Route to Claude<br>for continuation]
    CLAUDE_CHECK --> |No| NORMAL[Normal intent handling]

    ROUTE_CLAUDE --> RESPOND[Generate & play response]
    NORMAL --> RESPOND

    RESPOND --> ASK
```

## Claude Conversation Continuation

```mermaid
flowchart TD
    FOLLOWUP[Follow-up question received] --> PREV_CHECK{Previous intent<br>was Claude?}

    PREV_CHECK --> |No| NORMAL[Normal classification]
    PREV_CHECK --> |Yes| INTENT_CHECK{New intent type?}

    INTENT_CHECK --> |Timer/Reminder/Note/Time| SPECIFIC[Handle specific intent]
    INTENT_CHECK --> |General/Unknown| CONTINUE[Continue Claude conversation]

    CONTINUE --> CLAUDE[Send to Claude with context]
    CLAUDE --> RESPONSE[Claude generates response<br>with conversation history]

    SPECIFIC --> HANDLER[Route to specific handler]
    NORMAL --> CLASSIFY[Classify intent normally]
```

## TTS Synthesizer Selection

```mermaid
flowchart TD
    CREATE[create_synthesizer called] --> MOCK{use_mock=True?}

    MOCK --> |Yes| RETURN_MOCK[Return MockSynthesizer]
    MOCK --> |No| DETECT[Detect platform]

    DETECT --> ELEVEN{ElevenLabs<br>available & configured?}

    ELEVEN --> |Yes| RETURN_ELEVEN[Return ElevenLabsSynthesizer<br>with Bella voice]
    ELEVEN --> |No| PLATFORM{Platform?}

    PLATFORM --> |macOS| MACOS_CHECK{macOS say<br>available?}
    PLATFORM --> |Raspberry Pi| PI_CHECK{Piper TTS<br>available?}
    PLATFORM --> |Other| OTHER_CHECK{Piper TTS<br>available?}

    MACOS_CHECK --> |Yes| RETURN_MACOS[Return MacOSSynthesizer<br>with Samantha voice]
    MACOS_CHECK --> |No| MACOS_PIPER{Piper available?}

    MACOS_PIPER --> |Yes| RETURN_PIPER[Return PiperSynthesizer]
    MACOS_PIPER --> |No| RETURN_MOCK

    PI_CHECK --> |Yes| RETURN_PIPER
    PI_CHECK --> |No| RETURN_MOCK

    OTHER_CHECK --> |Yes| RETURN_PIPER
    OTHER_CHECK --> |No| RETURN_MOCK
```

## Emotion Detection (ElevenLabs)

```mermaid
flowchart TD
    TEXT[Response text] --> ANALYZE{Analyze text content}

    ANALYZE --> |hello/good morning/welcome| WARM[WARM emotion]
    ANALYZE --> |great!/awesome/excellent| CHEERFUL[CHEERFUL emotion]
    ANALYZE --> |sorry/error/problem| CONCERNED[CONCERNED emotion]
    ANALYZE --> |relax/take your time| CALM[CALM emotion]
    ANALYZE --> |weather/temperature/degrees| PROFESSIONAL[PROFESSIONAL emotion]
    ANALYZE --> |reminder/timer set| ENTHUSIASTIC[ENTHUSIASTIC emotion]
    ANALYZE --> |None of above| DEFAULT[WARM - default]

    WARM --> SYNTH[Synthesize with emotion cue]
    CHEERFUL --> SYNTH
    CONCERNED --> SYNTH
    CALM --> SYNTH
    PROFESSIONAL --> SYNTH
    ENTHUSIASTIC --> SYNTH
    DEFAULT --> SYNTH
```

## Summary

The conversation flow in Ara follows these key principles:

1. **Wake word activation**: Conversation starts with wake word detection
2. **Intent-driven routing**: User speech is classified and routed to appropriate handlers
3. **Continuous conversation**: After each response, Ara asks "Anything else?" to continue
4. **Smart continuation**: Claude conversations are maintained across follow-ups
5. **Graceful fallbacks**: TTS and other components have fallback chains
6. **Interrupt handling**: Users can interrupt responses with "stop" or "wait"
7. **Emotional TTS**: ElevenLabs responses include emotion detection for natural speech
