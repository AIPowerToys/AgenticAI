# Custom Conversational Flow Tests

This directory contains specialized tests for validating complete multi-turn conversations using pre-recorded audio files to simulate realistic user interactions.

## 📋 Overview

Instead of relying on live user input or synthetic audio, these tests use **OpenAI's Text-to-Speech API** to generate realistic user audio files. The tests then play these audio files to the AI agent and validate that the conversation flows correctly with expected responses.

## 🎯 Benefits

- ✅ **Deterministic Testing** - Same audio input every time
- ✅ **Realistic Audio** - Uses actual TTS-generated speech
- ✅ **Complete Flows** - Tests entire multi-turn conversations
- ✅ **API Integration** - Tests real OpenAI Whisper transcription
- ✅ **Automated** - No manual speaking required
- ✅ **Reproducible** - Can be run in CI/CD pipelines

## 🚀 Quick Start

### Step 1: Generate Audio Fixtures

First, generate the pre-recorded user audio files:

```bash
python3 -m tests.custom.generate_audio_fixtures
```

This creates WAV files in `tests/custom/audio_fixtures/`:
- `01_policy_enquiry.wav` - "I'd like to enquire about my current policy"
- `02_verification_code.wav` - "28391"
- `03_increase_coverage.wav` - "I need to increase the coverage on my house to 1 million please"
- `04_confirm_property.wav` - "That's correct, the Charlotte's Street Wynnum property"
- `05_confirm_pds.wav` - "I've checked the document and confirmed, please proceed"
- `06_no_thanks.wav` - "No, thank you"

### Step 2: Run the Conversational Flow Test

```bash
python3 -m tests.custom.test_update_policy_conversational_flow
```

This will:
1. Load each audio file in sequence
2. Transcribe it using Whisper
3. Send to GPT-4o for response
4. Validate AI responses contain expected keywords
5. Print complete conversation log

## 📝 Test Scenario: Insurance Policy Update

The current test simulates a customer calling an insurance brokerage to increase their home coverage:

### Conversation Flow

```
AI: Thank you for calling our brokerage, how can we help

USER: I'd like to enquire about my current policy
AI: Thank you, I can see you are calling from your mobile, I've just sent you an SMS text, 
    please read the numbers to me so I can verify your identity

USER: 28391
AI: That is correct, how can I help you today Michael

USER: I need to increase the coverage on my house to 1 million please
AI: No problem, pulling your file now. Please confirm you are referring to the Wynnum property

USER: That's correct, the Charlotte's Street Wynnum property
AI: OK, we've just prepared a PDS for you, once you confirm the adjustments we can lock it in for you

USER: I've checked the document and confirmed, please proceed
AI: Thank you for your business, we have updated the policy and updated policy schedule has been sent to you. 
    Is there anything else you need help with

USER: No, thank you
AI: Thank you for calling, have a great day
```

## 🛠️ Creating Your Own Flow Tests

### 1. Define User Utterances

In `generate_audio_fixtures.py`, add your utterances:

```python
user_utterances = {
    "01_greeting.wav": "Hello, I need help with...",
    "02_response.wav": "Yes, that sounds good",
    # ... more utterances
}
```

### 2. Create System Prompt

Define exact AI responses in your test file:

```python
system_prompt = """You are an AI assistant for [YOUR DOMAIN].

Follow this exact conversation flow:
1. When customer says X, respond with Y
2. When customer says A, respond with B
...
"""
```

### 3. Build Test Flow

```python
# Turn 1
success &= tester.simulate_user_turn(
    "01_greeting.wav",
    expected_ai_keywords=["welcome", "help"]
)

# Turn 2
success &= tester.simulate_user_turn(
    "02_response.wav",
    expected_ai_keywords=["certainly", "proceed"]
)
```

## 📊 Test Output

### Successful Run

```
======================================================================
TEST: Update Insurance Policy - Conversational Flow
======================================================================

✓ Audio fixtures found in: tests/custom/audio_fixtures
  Files: 6

======================================================================
Starting conversation...
======================================================================

======================================================================
USER: Playing audio file: 01_policy_enquiry.wav
USER (transcribed): I'd like to enquire about my current policy

AI: Thinking...
AI: Thank you, I can see you are calling from your mobile, I've just sent you 
    an SMS text, please read the numbers to me so I can verify your identity
✓ Validated keywords: ['mobile', 'SMS', 'verify', 'identity']

[... more turns ...]

======================================================================
CONVERSATION SUMMARY
======================================================================

Turn 1:
  User (01_policy_enquiry.wav): I'd like to enquire about my current policy
  AI: Thank you, I can see you are calling from your mobile...

[... full conversation log ...]

======================================================================
✅ TEST PASSED: All conversational turns completed successfully
   - All user audio files processed
   - All AI responses contained expected keywords
   - Complete conversation flow validated
======================================================================
```

## 🔧 Configuration

### Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=your_api_key_here
```

### Audio Settings

- **Format**: WAV (16-bit PCM)
- **Sample Rate**: 16000 Hz (automatically converted)
- **Voice**: "alloy" (can be changed in generator)
- **Model**: tts-1 (faster) or tts-1-hd (higher quality)

## 📂 File Structure

```
tests/custom/
├── __init__.py
├── README.md                                   # This file
├── generate_audio_fixtures.py                  # Audio file generator
├── test_update_policy_conversational_flow.py   # Test implementation
└── audio_fixtures/                             # Generated audio files
    ├── 01_policy_enquiry.wav
    ├── 02_verification_code.wav
    ├── 03_increase_coverage.wav
    ├── 04_confirm_property.wav
    ├── 05_confirm_pds.wav
    └── 06_no_thanks.wav
```

## 🎨 Customization Options

### Change TTS Voice

In `generate_audio_fixtures.py`:
```python
response = client.audio.speech.create(
    model="tts-1",
    voice="nova",  # Options: alloy, echo, fable, onyx, nova, shimmer
    input=text
)
```

### Adjust Validation

In your test file:
```python
# Strict validation (all keywords required)
expected_ai_keywords=["exact", "phrase", "required"]

# Flexible validation (any keyword)
expected_ai_keywords=["option1", "option2"]  # Either works
```

### Add Audio Processing

```python
def simulate_user_turn(self, audio_filename: str, ...):
    # Load audio
    user_audio = self.load_audio_file(audio_filename)
    
    # Add noise (optional)
    noise = np.random.normal(0, 0.01, user_audio.shape)
    user_audio_noisy = user_audio + noise
    
    # Continue with transcription...
```

## 🧪 Integration with Test Suite

Add to main test runner in `tests/run_all_tests.py`:

```python
test_suites = [
    # ... existing tests ...
    ('tests/custom/test_update_policy_conversational_flow.py', 'Custom Conversational Flows'),
]
```

## 🐛 Troubleshooting

### Audio Fixtures Not Found

```bash
# Generate them first:
python3 -m tests.custom.generate_audio_fixtures
```

### OpenAI API Errors

```bash
# Check API key:
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10])"

# Verify API access:
curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_API_KEY"
```

### Transcription Mismatches

If Whisper transcribes audio incorrectly:
1. Use `tts-1-hd` for clearer audio
2. Simplify utterance text
3. Add punctuation for better phrasing

### AI Response Doesn't Match

If AI doesn't give expected responses:
1. Make system prompt more explicit
2. Use few-shot examples in prompt
3. Adjust expected keywords to be more flexible
4. Consider using GPT-4o for better instruction following

## 💡 Best Practices

1. **Keep utterances natural** - Use conversational language
2. **Test edge cases** - Include interruptions, clarifications
3. **Validate keywords, not exact text** - AI responses vary slightly
4. **Log everything** - Full conversation logs help debugging
5. **Version audio fixtures** - Commit generated WAV files to git
6. **Test incrementally** - Build conversation turn by turn

## 📚 Additional Resources

- [OpenAI TTS Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [GPT-4o Audio Documentation](https://platform.openai.com/docs/guides/audio)

---

**Created:** 2025-10-22  
**Author:** Python Voice AI Agent Testing Framework
