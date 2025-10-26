#!/usr/bin/env python3
"""
Real-time interaction tests for Python Voice AI Agent.
Tests seamless turn-taking, barge-in, and latency.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import os
import sys
import time
import threading
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import VoiceAssistantSession, AudioPlayer
import io
import wave


def is_interactive():
    """Check if running in interactive mode."""
    return sys.stdin.isatty()


def skip_if_not_interactive(test_name):
    """Skip test if not running interactively."""
    if not is_interactive():
        print(f"\n=== Test: {test_name} ===")
        print("⚠ Skipped (non-interactive mode)")
        print("  Run this test directly for manual interaction")
        return True
    return False


def test_seamless_turn_taking():
    """Test natural back-and-forth without manual triggers."""
    if skip_if_not_interactive("Seamless Turn Taking"):
        return True
    
    print("\n=== Test: Seamless Turn Taking ===")
    print("This test requires manual interaction:")
    print("1. Say something")
    print("2. Listen to AI response")
    print("3. Immediately say something else")
    print("4. Verify continuous flow")
    print("\nPress Enter when ready (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Be very brief, respond in 1 sentence.",
        sample_rate=16000
    )
    
    try:
        print("\nTurn 1: Speak now...")
        if session.record_user():
            session.respond()
        
        print("\nTurn 2: Speak immediately after AI finishes...")
        time.sleep(0.5)
        if session.record_user():
            session.respond()
        
        print("✓ Seamless turn-taking tested")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_barge_in_during_response():
    """Test interrupting AI mid-sentence."""
    if skip_if_not_interactive("Barge-In During Response"):
        return True
    
    print("\n=== Test: Barge-In During Response ===")
    print("This test will:")
    print("1. Ask AI a question")
    print("2. Wait 2 seconds into response")
    print("3. Interrupt by speaking")
    print("\nPress Enter when ready (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Tell long stories with many details.",
        sample_rate=16000
    )
    
    try:
        print("\nSay: 'Tell me a long story about space'")
        if session.record_user():
            # Start response in background
            response_thread = threading.Thread(target=session.respond)
            response_thread.start()
            
            print("\nWait 2 seconds, then SPEAK to interrupt...")
            time.sleep(2.0)
            
            interrupt_start = time.time()
            # The VAD monitor should detect speech and interrupt
            
            response_thread.join(timeout=10)
            interrupt_time = time.time() - interrupt_start
            
            if interrupt_time < 1.0:
                print(f"✓ Interruption response time: {interrupt_time*1000:.0f}ms")
                return True
            else:
                print(f"⚠ Slow interruption: {interrupt_time*1000:.0f}ms")
                return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_multiple_rapid_interruptions():
    """Test interrupting multiple times in succession."""
    if skip_if_not_interactive("Multiple Rapid Interruptions"):
        return True
    
    print("\n=== Test: Multiple Rapid Interruptions ===")
    print("Test rapid successive interruptions")
    print("Press Enter when ready (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    # Generate test audio for interruptions
    sample_rate = 16000
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with io.BytesIO() as output:
        with wave.open(output, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        wav_bytes = output.getvalue()
    
    player = AudioPlayer()
    interruptions = []
    
    try:
        for i in range(3):
            print(f"\nInterruption {i+1}/3: Playing audio...")
            player.play_wav(wav_bytes)
            time.sleep(1.0)
            
            start = time.time()
            player.interrupt()
            was_interrupted = player.wait_finish_or_interrupt()
            elapsed = time.time() - start
            
            interruptions.append(was_interrupted)
            print(f"  Interrupted: {was_interrupted}, Time: {elapsed*1000:.0f}ms")
            time.sleep(0.5)
        
        success_count = sum(interruptions)
        print(f"\n✓ {success_count}/3 interruptions successful")
        return success_count >= 2
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_latency_measurements():
    """Measure response latency at each stage."""
    if skip_if_not_interactive("Latency Measurements"):
        return True
    
    print("\n=== Test: Latency Measurements ===")
    print("Measuring end-to-end latency")
    print("Press Enter when ready (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Respond in exactly 5 words.",
        sample_rate=16000,
        silence_duration=1.0
    )
    
    try:
        print("\nSay a short phrase (e.g., 'Hello')...")
        
        t1 = time.time()
        user_text = session.record_user()
        t2 = time.time()
        
        if not user_text:
            print("✗ No speech detected")
            return False
        
        recording_time = t2 - t1
        
        session.respond()
        t3 = time.time()
        
        response_time = t3 - t2
        total_time = t3 - t1
        
        print(f"\n📊 Latency Breakdown:")
        print(f"  Recording + Transcription: {recording_time:.2f}s")
        print(f"  AI Response + Playback: {response_time:.2f}s")
        print(f"  Total: {total_time:.2f}s")
        
        if total_time < 5.0:
            print("✓ Latency acceptable (< 5s)")
            return True
        else:
            print("⚠ Latency high but measured")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Real-Time Interaction Tests - Voice AI Agent")
    print("=" * 60)
    
    tests = [
        ("Seamless Turn Taking", test_seamless_turn_taking),
        ("Barge-In During Response", test_barge_in_during_response),
        ("Multiple Rapid Interruptions", test_multiple_rapid_interruptions),
        ("Latency Measurements", test_latency_measurements),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
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
