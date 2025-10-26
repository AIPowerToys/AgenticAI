# Python Voice AI Agent - Testing Guide

This document provides comprehensive documentation for the test suite designed to validate production-level voice conversation capabilities.

## Overview

This test suite validates **40+ test scenarios** across 6 major categories to ensure natural, AI-powered voice interaction quality.

## Test Categories

### 1. **Real-Time Interaction Tests** (`test_realtime_interaction.py`)
Tests natural conversation flow and interruption handling:
- ✅ Seamless turn-taking without manual triggers
- ✅ Barge-in during AI response (interruption)
- ✅ Multiple rapid interruptions
- ✅ End-to-end latency measurements

**Key Metrics:**
- Latency: < 3s from speech end to response start
- Interruption response: < 200ms to stop playback

### 2. **Conversation Context Tests** (`test_conversation_context.py`)
Tests memory and context retention:
- ✅ Multi-turn context retention (3+ turns)
- ✅ Long conversation memory (10+ turns)
- ✅ Context preservation after interruption
- ✅ History reset functionality

**Key Metrics:**
- Context retention: 10+ turns without degradation
- Proper history management and cleanup

### 3. **Speech Quality & Robustness Tests** (`test_speech_quality.py`)
Tests speech detection accuracy:
- ✅ Background noise rejection
- ✅ Echo cancellation (speaker audio filtering)
- ✅ Far-field speech detection
- ✅ Whisper vs loud speech handling
- ✅ Continuous vs intermittent speech patterns

**Key Metrics:**
- VAD accuracy: > 95% speech detection
- False positive rate: < 1%

### 4. **Error Recovery Tests** (`test_error_recovery.py`)
Tests graceful error handling:
- ✅ API timeout recovery
- ✅ Transcription failure handling
- ✅ No speech detected timeout
- ✅ Invalid audio format handling
- ✅ Session state management (is_responding flag)
- ✅ Network error simulation

**Key Metrics:**
- No crashes on API failures
- Clean history management on errors

### 5. **Performance & Reliability Tests** (`test_performance.py`)
Tests system performance and stability:
- ✅ Memory usage monitoring
- ✅ Audio processing latency
- ✅ Concurrent session isolation
- ✅ Rapid audio operations stability
- ✅ Long history performance
- ✅ Threading stability

**Key Metrics:**
- Memory increase: < 100MB for typical session
- Processing latency: < 100ms for 10s audio
- Uptime: > 99% for 30-minute sessions

### 6. **Comprehensive VAD Tests** (`test_voice_assistant_VAD_comprehensive.py`)
Low-level component tests:
- ✅ Edge cases (empty audio, sample rates, clipping)
- ✅ VAD parameters (aggressiveness, chunk sizes)
- ✅ Audio player operations
- ✅ Performance benchmarks

## Quick Start

### Run All Tests
```bash
python3 run_all_chatgpt_parity_tests.py
```

This will:
1. Run all 6 test suites sequentially
2. Generate a summary report
3. Save detailed results to `test_report_TIMESTAMP.txt`

### Run Individual Test Suites

```bash
# Real-time interaction
python3 test_realtime_interaction.py

# Conversation context
python3 test_conversation_context.py

# Speech quality
python3 test_speech_quality.py

# Error recovery
python3 test_error_recovery.py

# Performance
python3 test_performance.py

# Comprehensive VAD
python3 test_voice_assistant_VAD_comprehensive.py
```

## Test Types

### Automated Tests
These run without user interaction:
- Component tests (VAD, audio player, etc.)
- Error recovery simulations
- Performance benchmarks
- Memory monitoring

### Manual Interaction Tests
These require speaking into the microphone:
- Real-time conversation flow
- Interruption/barge-in scenarios
- Speech quality at different volumes
- Multi-turn conversations

**Note:** Manual tests can be skipped by entering 's' when prompted.

## Requirements

```bash
# Core dependencies
pip install openai python-dotenv sounddevice webrtcvad simpleaudio numpy

# Performance monitoring
pip install psutil
```

## Environment Setup

Create a `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
SYTEM_PROMPT="You are a helpful voice assistant."
```

## Performance Benchmarks

To achieve production-quality voice AI, your system should meet:

| Metric | Target | Test |
|--------|--------|------|
| Response Latency | < 3s | test_realtime_interaction.py |
| Interruption Response | < 200ms | test_realtime_interaction.py |
| VAD Accuracy | > 95% | test_speech_quality.py |
| False Positives | < 1% | test_speech_quality.py |
| Context Retention | 10+ turns | test_conversation_context.py |
| Memory Growth | < 100MB | test_performance.py |
| Audio Processing | < 100ms/10s | test_performance.py |
| Error Recovery | 100% | test_error_recovery.py |

## Test Results Interpretation

### ✓ PASS
Test executed successfully and met expected criteria.

### ⚠ Skipped
Test was skipped (manual test or missing API key).

### ✗ FAIL
Test failed - indicates potential issue with implementation.

## Common Issues

### Tests Skip Automatically
- **Cause:** No `OPENAI_API_KEY` in `.env`
- **Fix:** Add valid API key to `.env` file

### Manual Tests Timeout
- **Cause:** No speech detected or silence duration too long
- **Fix:** Speak clearly within 2-3 seconds of prompt

### High Latency
- **Cause:** Slow network or API response
- **Fix:** Check internet connection, try different time

### VAD False Triggers
- **Cause:** Background noise or speaker echo
- **Fix:** Use quieter environment, adjust VAD aggressiveness

## Advanced Testing

### Custom Test Scenarios

You can add your own tests by following the pattern:

```python
def test_custom_scenario():
    """Test description."""
    print("\n=== Test: Custom Scenario ===")
    
    try:
        # Your test logic here
        print("✓ Test passed")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
```

### Continuous Integration

Add to CI/CD pipeline:

```yaml
# .github/workflows/voice_tests.yml
- name: Run Voice Assistant Tests
  run: python3 run_all_chatgpt_parity_tests.py
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Performance Profiling

For detailed performance analysis:

```python
import cProfile
import pstats

cProfile.run('session.turn()', 'profile_stats')
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(20)
```

## Troubleshooting

### Audio Device Issues
```bash
# List available audio devices
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

### VAD Not Detecting Speech
- Try different aggressiveness levels (0-3)
- Ensure microphone is working
- Check audio format (must be 16kHz, mono, int16)

### Memory Leaks
Run memory profiling:
```bash
pip install memory_profiler
python3 -m memory_profiler test_performance.py
```

## Contributing

To add new tests:

1. Create test file following naming convention: `test_[category].py`
2. Implement test functions with clear docstrings
3. Add to `run_all_chatgpt_parity_tests.py` test_suites list
4. Update this README with test description

## License

Same as main project.

## Support

For issues or questions about the test suite, check:
- Test output logs
- Generated report files
- Voice assistant implementation (`voice_assistant_VAD.py`)
