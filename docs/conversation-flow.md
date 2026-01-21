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

    CLASSIFY --> |7a: Note/Remember| NOTE_FLOW[8a: Note Capture Flow]
    CLASSIFY --> |7b: Ask Claude| CLAUDE_FLOW[8b: Claude Query Flow]
    CLASSIFY --> |7c: Search/Google| WEB_FLOW[8c: Web Search Flow]
    CLASSIFY --> |7d: Ask Perplexity| PERPLEXITY_FLOW[8d: Perplexity Flow]
    CLASSIFY --> |7z: Other| ROUTER_FLOW[8z: QueryRouter Flow]

    NOTE_FLOW --> SYNTHESIZE[9. Synthesize response]
    CLAUDE_FLOW --> SYNTHESIZE
    WEB_FLOW --> SYNTHESIZE
    PERPLEXITY_FLOW --> SYNTHESIZE
    ROUTER_FLOW --> SYNTHESIZE

    SYNTHESIZE --> PLAY[10. Play response audio]

    PLAY --> NOTE_CHECK{11. Note mode?}
    NOTE_CHECK --> |Yes| LISTEN
    NOTE_CHECK --> |No| ANYTHING_ELSE[12. Ask Anything else?]

    ANYTHING_ELSE --> AE_LISTEN[13. Listen for response]
    AE_LISTEN --> |No response/silence| GOODBYE[20. Say goodbye]
    AE_LISTEN --> |Response detected| AE_TRANSCRIBE[14. Transcribe response]

    AE_TRANSCRIBE --> AE_CHECK{15. User response}
    AE_CHECK --> |No/Thanks/negative| GOODBYE
    AE_CHECK --> |Yes/affirmative only| PROMPT[16. Ask What else?]
    AE_CHECK --> |Contains question| PROCESS_FOLLOWUP[17. Process question]

    PROMPT --> PROMPT_LISTEN[16a. Listen for question]
    PROMPT_LISTEN --> |No response| GOODBYE
    PROMPT_LISTEN --> |Question received| PROCESS_FOLLOWUP

    PROCESS_FOLLOWUP --> CLASSIFY_FOLLOWUP[18. Classify follow-up intent]
    CLASSIFY_FOLLOWUP --> CLAUDE_CHECK{19. Previous was Claude?}

    CLAUDE_CHECK --> |Yes and general question| ROUTE_CLAUDE[19a. Route to Claude]
    CLAUDE_CHECK --> |No or specific intent| HANDLE_FOLLOWUP[19b. Handle intent normally]

    ROUTE_CLAUDE --> SYNTH_FOLLOWUP[19c. Synthesize response]
    HANDLE_FOLLOWUP --> SYNTH_FOLLOWUP

    SYNTH_FOLLOWUP --> PLAY_FOLLOWUP[19d. Play response]
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
| 8a | Note Capture Flow - See detailed diagram below |
| 8b | Claude Query Flow - See detailed diagram below |
| 8c | Web Search Flow - See detailed diagram below |
| 8d | Perplexity Flow - See detailed diagram below |
| 8z | QueryRouter Flow - See detailed diagram below |
| 9 | Synthesize response - Generate TTS audio |
| 10 | Play response audio - Speak response |
| 11 | Note mode? - Check for continuation |
| 12 | Ask "Anything else?" - Prompt for follow-up |
| 13 | Listen for response - Wait for user reply |
| 14 | Transcribe response - Convert reply to text |
| 15 | User response - Decision point |
| 16 | Ask "What else?" - Prompt for question |
| 16a | Listen for question - Wait for follow-up |
| 17 | Process question - Handle follow-up |
| 18 | Classify follow-up intent - Categorize |
| 19 | Previous was Claude? - Check conversation context |
| 19a | Route to Claude - Continue Claude conversation |
| 19b | Handle intent normally - Standard processing |
| 19c | Synthesize response - Generate follow-up TTS |
| 19d | Play response - Speak follow-up |
| 20 | Say goodbye - End interaction |

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

## 7a: Note Capture Flow

```mermaid
flowchart TD
    START[7a: Note/Remember detected] --> CONFIRM[8a.1: Say Ready]
    CONFIRM --> RECORD[8a.2: Record speech]
    RECORD --> CHECK{8a.3: Done Ara heard?}

    CHECK --> |No| RECORD
    CHECK --> |Yes| TRANSCRIBE[8a.4: Transcribe all recordings]

    TRANSCRIBE --> EXTRACT[8a.5: Extract action items via LLM]
    EXTRACT --> SAVE[8a.6: Save to MongoDB]
    SAVE --> RESPONSE[8a.7: Noted. X action items saved.]
    RESPONSE --> LISTEN([Return to wake word])
```

| Step | Description |
|------|-------------|
| 8a.1 | Confirm note mode with "Ready" |
| 8a.2 | Continuous recording of user speech |
| 8a.3 | Monitor for "Done Ara" stop phrase |
| 8a.4 | Transcribe accumulated audio |
| 8a.5 | Use LLM to extract action items from transcript |
| 8a.6 | Store notes and action items in MongoDB |
| 8a.7 | Confirm with count of action items saved |

## 7b: Claude Query Flow

```mermaid
flowchart TD
    START[7b: Ask Claude detected] --> EXTRACT[8b.1: Extract query from transcript]
    EXTRACT --> SEND[8b.2: Send to Claude API]
    SEND --> RECEIVE[8b.3: Receive response]
    RECEIVE --> STORE[8b.4: Store conversation context]
    STORE --> SYNTH([Continue to Synthesize])
```

| Step | Description |
|------|-------------|
| 8b.1 | Parse user query from transcript |
| 8b.2 | Send query to Claude API with system prompt |
| 8b.3 | Receive Claude response |
| 8b.4 | Store context for follow-up questions |

## 7c: Web Search Flow (Tavily)

```mermaid
flowchart TD
    START[7c: Search/Google detected] --> EXTRACT[8c.1: Extract search query]
    EXTRACT --> SEARCH[8c.2: Send to Tavily API]
    SEARCH --> PARSE[8c.3: Parse search results]
    PARSE --> FORMAT[8c.4: Format answer for voice]
    FORMAT --> SYNTH([Continue to Synthesize])
```

| Step | Description |
|------|-------------|
| 8c.1 | Extract search query from transcript |
| 8c.2 | Execute web search via Tavily API |
| 8c.3 | Parse and rank search results |
| 8c.4 | Format concise answer suitable for voice |

## 7d: Perplexity Search Flow

```mermaid
flowchart TD
    START[7d: Ask Perplexity detected] --> EXTRACT[8d.1: Extract search query]
    EXTRACT --> SEND[8d.2: Send to Perplexity API]
    SEND --> RECEIVE[8d.3: Receive AI-enhanced answer]
    RECEIVE --> CLEAN[8d.4: Clean citation markers]
    CLEAN --> SYNTH([Continue to Synthesize])
```

| Step | Description |
|------|-------------|
| 8d.1 | Extract search query from transcript |
| 8d.2 | Send query to Perplexity chat completions API |
| 8d.3 | Receive AI-synthesized answer with citations |
| 8d.4 | Remove [1][2] citation markers for clean voice output |

## 7z: QueryRouter Flow (Default)

```mermaid
flowchart TD
    START[7z: Other query detected] --> ANALYZE{8z.1: Analyze query type}

    ANALYZE --> |Personal data query| MONGO[8z.2a: Query MongoDB]
    ANALYZE --> |Factual/current events| TAVILY[8z.2b: Search Tavily]
    ANALYZE --> |General knowledge| OLLAMA[8z.2c: Query Ollama LLM]

    MONGO --> FORMAT[8z.3: Format response]
    TAVILY --> FORMAT
    OLLAMA --> FORMAT

    FORMAT --> SYNTH([Continue to Synthesize])
```

| Step | Description |
|------|-------------|
| 8z.1 | Classify query as personal, factual, or general |
| 8z.2a | Personal: Query MongoDB for notes, activities, etc. |
| 8z.2b | Factual: Execute web search via Tavily |
| 8z.2c | General: Generate response via local Ollama LLM |
| 8z.3 | Format response for voice output |

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
