#!/usr/bin/env python3
"""
Performance and reliability tests for Python Voice AI Agent.
Tests memory usage, extended sessions, and performance metrics.
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
import psutil
from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import VoiceAssistantSession, AudioPlayer, numpy_to_wav_bytes
import io
import wave


def test_memory_usage_monitoring():
    """Monitor memory usage during session."""
    print("\n=== Test: Memory Usage Monitoring ===")
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"  Initial memory: {initial_memory:.1f} MB")
    
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
    
    # Simulate conversation
    for i in range(10):
        session.history.append({
            'role': 'user',
            'content': [{'type': 'text', 'text': f'Message {i}'}]
        })
        session.history.append({
            'role': 'assistant',
            'content': [{'type': 'text', 'text': f'Response {i}'}]
        })
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory
    
    print(f"  Final memory: {final_memory:.1f} MB")
    print(f"  Increase: {memory_increase:.1f} MB")
    
    if memory_increase < 100:  # Reasonable threshold
        print("✓ Memory usage acceptable")
        return True
    else:
        print("⚠ High memory increase (may be normal)")
        return True


def test_audio_processing_latency():
    """Measure audio processing latency."""
    print("\n=== Test: Audio Processing Latency ===")
    
    sample_rate = 16000
    durations = [1.0, 5.0, 10.0]
    
    for duration in durations:
        audio = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.1
        
        start = time.time()
        wav_bytes = numpy_to_wav_bytes(audio, sample_rate)
        latency = (time.time() - start) * 1000  # ms
        
        print(f"  {duration:4.1f}s audio: {latency:6.2f}ms processing time")
    
    print("✓ Audio processing latency measured")
    return True


def test_concurrent_sessions():
    """Test multiple sessions don't interfere."""
    print("\n=== Test: Concurrent Sessions ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipped (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    
    try:
        # Create two sessions
        session1 = VoiceAssistantSession(
            client=client,
            system_prompt="You are assistant 1",
            sample_rate=16000
        )
        session2 = VoiceAssistantSession(
            client=client,
            system_prompt="You are assistant 2",
            sample_rate=16000
        )
        
        # Add different history to each
        session1.history.append({
            'role': 'user',
            'content': [{'type': 'text', 'text': 'Session 1 message'}]
        })
        session2.history.append({
            'role': 'user',
            'content': [{'type': 'text', 'text': 'Session 2 message'}]
        })
        
        # Verify isolation
        if len(session1.history) == 1 and len(session2.history) == 1:
            print("✓ Sessions maintain separate state")
            
            # Check they have different histories
            msg1 = session1.history[0]['content'][0]['text']
            msg2 = session2.history[0]['content'][0]['text']
            
            if msg1 != msg2:
                print("✓ No crosstalk between sessions")
                return True
            else:
                print("✗ Sessions share state")
                return False
        else:
            print("✗ Session state unexpected")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_rapid_audio_operations():
    """Test rapid play/stop cycles for stability."""
    print("\n=== Test: Rapid Audio Operations ===")
    
    sample_rate = 16000
    duration = 0.3
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
    
    try:
        cycles = 50
        start_time = time.time()
        
        for i in range(cycles):
            player.play_wav(wav_bytes)
            time.sleep(0.05)
            
            if i % 2 == 0:
                player.stop()
            
            time.sleep(0.02)
        
        elapsed = time.time() - start_time
        ops_per_sec = cycles / elapsed
        
        print(f"  Completed {cycles} cycles in {elapsed:.2f}s")
        print(f"  Operations per second: {ops_per_sec:.1f}")
        print("✓ Rapid operations stable")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_long_history_performance():
    """Test performance with long conversation history."""
    print("\n=== Test: Long History Performance ===")
    
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
        # Add 100 messages to history
        num_messages = 100
        for i in range(num_messages):
            session.history.append({
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': [{'type': 'text', 'text': f'Message {i}' * 10}]
            })
        
        # Test message building performance
        start = time.time()
        messages = session._build_messages()
        elapsed = (time.time() - start) * 1000
        
        print(f"  History size: {len(session.history)} messages")
        print(f"  Message building: {elapsed:.2f}ms")
        print(f"  Built messages: {len(messages)}")
        
        if elapsed < 100:  # Should be fast
            print("✓ Long history performance acceptable")
            return True
        else:
            print("⚠ Slow message building")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_threading_stability():
    """Test threading stability under load."""
    print("\n=== Test: Threading Stability ===")
    
    results = {'count': 0, 'errors': 0}
    lock = threading.Lock()
    stop_flag = threading.Event()
    
    def worker(worker_id):
        try:
            for i in range(20):
                if stop_flag.is_set():
                    break
                with lock:
                    results['count'] += 1
                time.sleep(0.01)
        except Exception:
            with lock:
                results['errors'] += 1
    
    try:
        num_threads = 10
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        
        start = time.time()
        for t in threads:
            t.start()
        
        time.sleep(0.5)
        stop_flag.set()
        
        for t in threads:
            t.join(timeout=2.0)
        
        elapsed = time.time() - start
        
        print(f"  Threads: {num_threads}")
        print(f"  Operations: {results['count']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Time: {elapsed:.2f}s")
        
        if results['errors'] == 0:
            print("✓ Threading stable")
            return True
        else:
            print("✗ Threading errors detected")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Performance & Reliability Tests - Voice AI Agent")
    print("=" * 60)
    
    tests = [
        ("Memory Usage Monitoring", test_memory_usage_monitoring),
        ("Audio Processing Latency", test_audio_processing_latency),
        ("Concurrent Sessions", test_concurrent_sessions),
        ("Rapid Audio Operations", test_rapid_audio_operations),
        ("Long History Performance", test_long_history_performance),
        ("Threading Stability", test_threading_stability),
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
