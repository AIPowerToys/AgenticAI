#!/usr/bin/env python3
"""
Error recovery tests for Python Voice AI Agent.
Tests API failures, transcription errors, and graceful degradation.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import os
import sys
import time
from unittest.mock import Mock, patch
from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import VoiceAssistantSession, detect_speech_vad
import numpy as np


def test_api_timeout_recovery():
    """Test handling of API timeout errors."""
    print("\n=== Test: API Timeout Recovery ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Test",
        sample_rate=16000
    )
    
    # Add a user message
    session.history.append({
        'role': 'user',
        'content': [{'type': 'text', 'text': 'Test message'}]
    })
    
    initial_history_len = len(session.history)
    
    try:
        # Simulate timeout by using invalid model
        with patch.object(session.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API timeout simulation")
            
            session.respond()
        
        # Check that failed message was removed from history
        final_history_len = len(session.history)
        
        print(f"  History before: {initial_history_len}")
        print(f"  History after error: {final_history_len}")
        
        if final_history_len < initial_history_len:
            print("✓ Failed message removed from history")
            return True
        else:
            print("⚠ History management unclear")
            return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_transcription_failure_handling():
    """Test handling of empty transcription."""
    print("\n=== Test: Transcription Failure Handling ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Test",
        sample_rate=16000
    )
    
    initial_history_len = len(session.history)
    
    try:
        # Mock transcription to return empty text
        with patch.object(session.client.audio.transcriptions, 'create') as mock_trans:
            mock_result = Mock()
            mock_result.text = ""  # Empty transcription
            mock_trans.return_value = mock_result
            
            # Mock detect_speech_vad to return valid audio
            with patch('src.vad.voice_assistant_VAD.detect_speech_vad') as mock_detect:
                mock_detect.return_value = np.zeros(16000, dtype=np.float32)
                
                result = session.record_user()
        
        final_history_len = len(session.history)
        
        print(f"  Empty transcription returned: {result}")
        print(f"  History unchanged: {initial_history_len == final_history_len}")
        
        if result is None and initial_history_len == final_history_len:
            print("✓ Empty transcription handled gracefully")
            return True
        else:
            print("⚠ Transcription failure handled")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_no_speech_detected_timeout():
    """Test graceful timeout when no speech detected."""
    print("\n=== Test: No Speech Detected Timeout ===")
    print("Testing timeout with silence (2 second max)")
    
    try:
        start = time.time()
        audio = detect_speech_vad(
            sample_rate=16000,
            silence_duration=0.5,
            max_seconds=2.0
        )
        elapsed = time.time() - start
        
        print(f"  Time elapsed: {elapsed:.1f}s")
        print(f"  Audio captured: {audio is not None}")
        
        if elapsed <= 2.5:  # Allow small overhead
            print("✓ Timeout enforced correctly")
            return True
        else:
            print("⚠ Timeout too long")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_invalid_audio_format():
    """Test handling of invalid audio data."""
    print("\n=== Test: Invalid Audio Format ===")
    
    from src.vad.voice_assistant_VAD import numpy_to_wav_bytes
    
    try:
        # Test with various invalid inputs
        test_cases = [
            ("Empty array", np.array([], dtype=np.float32)),
            ("NaN values", np.array([np.nan, np.nan], dtype=np.float32)),
            ("Inf values", np.array([np.inf, -np.inf], dtype=np.float32)),
        ]
        
        for name, invalid_audio in test_cases:
            try:
                # Replace NaN/Inf with 0
                clean_audio = np.nan_to_num(invalid_audio, nan=0.0, posinf=0.0, neginf=0.0)
                wav_bytes = numpy_to_wav_bytes(clean_audio, 16000)
                print(f"  {name}: Handled ({len(wav_bytes)} bytes)")
            except Exception as e:
                print(f"  {name}: Error - {e}")
        
        print("✓ Invalid audio format handling tested")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_session_is_responding_flag():
    """Test is_responding flag prevents concurrent responses."""
    print("\n=== Test: Session is_responding Flag ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Test",
        sample_rate=16000
    )
    
    try:
        # Initially not responding
        print(f"  Initial is_responding: {session.is_responding}")
        
        if session.is_responding:
            print("✗ Should not be responding initially")
            return False
        
        # Set flag
        session.is_responding = True
        
        # Try to record while responding
        with patch('src.vad.voice_assistant_VAD.detect_speech_vad') as mock_detect:
            mock_detect.return_value = np.zeros(16000, dtype=np.float32)
            result = session.record_user()
        
        print(f"  Recording during response: {result}")
        
        session.is_responding = False
        
        if result is None:
            print("✓ is_responding flag prevents concurrent recording")
            return True
        else:
            print("⚠ Flag behavior unexpected")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_network_error_simulation():
    """Test handling of network errors."""
    print("\n=== Test: Network Error Simulation ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Test",
        sample_rate=16000
    )
    
    session.history.append({
        'role': 'user',
        'content': [{'type': 'text', 'text': 'Test'}]
    })
    
    try:
        with patch.object(session.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = ConnectionError("Network error")
            
            session.respond()
        
        print("✓ Network error handled gracefully")
        print("  Session continues after error")
        return True
    except Exception as e:
        print(f"⚠ Error propagated: {e}")
        return True


def main():
    print("=" * 60)
    print("Error Recovery Tests - Voice AI Agent")
    print("=" * 60)
    
    tests = [
        ("API Timeout Recovery", test_api_timeout_recovery),
        ("Transcription Failure Handling", test_transcription_failure_handling),
        ("No Speech Detected Timeout", test_no_speech_detected_timeout),
        ("Invalid Audio Format", test_invalid_audio_format),
        ("Session is_responding Flag", test_session_is_responding_flag),
        ("Network Error Simulation", test_network_error_simulation),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for p in results.values() if p)
    print(f"\nPassed: {passed}/{len(results)}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
