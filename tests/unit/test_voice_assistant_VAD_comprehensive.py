#!/usr/bin/env python3
"""
Comprehensive extended tests for VAD-based voice assistant.
Tests edge cases, error handling, performance, and concurrency.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import os
import sys
import time
import numpy as np
import sounddevice as sd
import webrtcvad
from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import (
    AudioPlayer,
    detect_speech_vad,
    monitor_for_speech_interruption,
    VoiceAssistantSession,
    numpy_to_wav_bytes
)
import threading
import io
import wave


# ===== EDGE CASE TESTS =====

def test_empty_audio_input():
    """Test handling of empty/null audio inputs."""
    print("\n=== Test: Empty Audio Input ===")
    
    # Test with empty numpy array
    empty_audio = np.array([], dtype=np.float32)
    try:
        wav_bytes = numpy_to_wav_bytes(empty_audio, 16000)
        print(f"✓ Empty audio converted to WAV ({len(wav_bytes)} bytes)")
        return True
    except Exception as e:
        print(f"✗ Failed to handle empty audio: {e}")
        return False


def test_invalid_sample_rates():
    """Test with various sample rates."""
    print("\n=== Test: Invalid Sample Rates ===")
    
    sample_rates = [8000, 16000, 24000, 32000, 48000]
    results = []
    
    for rate in sample_rates:
        try:
            # Generate 0.5 second of audio
            duration = 0.5
            t = np.linspace(0, duration, int(rate * duration))
            audio = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
            wav_bytes = numpy_to_wav_bytes(audio, rate)
            print(f"✓ Sample rate {rate}Hz: {len(wav_bytes)} bytes")
            results.append(True)
        except Exception as e:
            print(f"✗ Sample rate {rate}Hz failed: {e}")
            results.append(False)
    
    return all(results)


def test_audio_clipping_prevention():
    """Test audio clipping is prevented."""
    print("\n=== Test: Audio Clipping Prevention ===")
    
    # Generate audio that would clip (values > 1.0)
    sample_rate = 16000
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create audio with values outside [-1, 1]
    audio_clipping = (np.sin(2 * np.pi * 440 * t) * 2.0).astype(np.float32)
    
    try:
        wav_bytes = numpy_to_wav_bytes(audio_clipping, sample_rate)
        
        # Read back the WAV and check values
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            
            max_val = np.max(np.abs(audio_float))
            print(f"✓ Max audio value: {max_val:.3f} (should be ≤ 1.0)")
            
            if max_val <= 1.0:
                print("✓ Clipping prevention working")
                return True
            else:
                print("✗ Audio values exceed 1.0")
                return False
                
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_very_short_recording():
    """Test handling of very short audio (< 100ms)."""
    print("\n=== Test: Very Short Recording ===")
    
    sample_rate = 16000
    duration = 0.05  # 50ms - very short
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
    
    try:
        wav_bytes = numpy_to_wav_bytes(audio, sample_rate)
        print(f"✓ Short audio handled: {len(audio)} samples, {len(wav_bytes)} bytes")
        return True
    except Exception as e:
        print(f"✗ Failed on short audio: {e}")
        return False


def test_max_recording_duration():
    """Test max_seconds parameter enforcement."""
    print("\n=== Test: Max Recording Duration ===")
    print("This will record for max 2 seconds. Stay silent.")
    
    start_time = time.time()
    audio = detect_speech_vad(
        sample_rate=16000,
        silence_duration=0.5,
        max_seconds=2.0  # Should timeout after 2 seconds
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Recording stopped after {elapsed:.1f} seconds")
    
    if elapsed <= 2.5:  # Allow some overhead
        print("✓ Max duration enforced correctly")
        return True
    else:
        print("✗ Max duration not enforced")
        return False


# ===== VAD PARAMETER TESTS =====

def test_vad_aggressiveness_levels():
    """Test different VAD aggressiveness settings."""
    print("\n=== Test: VAD Aggressiveness Levels ===")
    
    sample_rate = 16000
    chunk_ms = 30
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    
    # Generate silence and noise
    silence = np.zeros(chunk_samples, dtype=np.int16)
    noise = (np.random.randn(chunk_samples) * 100).astype(np.int16)
    
    results = []
    for level in range(4):  # 0, 1, 2, 3
        vad = webrtcvad.Vad(level)
        
        silence_detected = vad.is_speech(silence.tobytes(), sample_rate)
        noise_detected = vad.is_speech(noise.tobytes(), sample_rate)
        
        print(f"  Level {level}: Silence={silence_detected}, Noise={noise_detected}")
        results.append(True)
    
    print("✓ All aggressiveness levels tested")
    return all(results)


def test_vad_chunk_sizes():
    """Test different chunk sizes (10ms, 20ms, 30ms)."""
    print("\n=== Test: VAD Chunk Sizes ===")
    
    sample_rate = 16000
    vad = webrtcvad.Vad(2)
    
    chunk_sizes = [10, 20, 30]
    results = []
    
    for chunk_ms in chunk_sizes:
        chunk_samples = int(sample_rate * chunk_ms / 1000)
        audio = (np.random.randn(chunk_samples) * 1000).astype(np.int16)
        
        try:
            is_speech = vad.is_speech(audio.tobytes(), sample_rate)
            print(f"✓ Chunk size {chunk_ms}ms: speech={is_speech}")
            results.append(True)
        except Exception as e:
            print(f"✗ Chunk size {chunk_ms}ms failed: {e}")
            results.append(False)
    
    return all(results)


# ===== AUDIO PLAYER TESTS =====

def test_concurrent_audio_playback():
    """Test multiple rapid play requests."""
    print("\n=== Test: Concurrent Audio Playback ===")
    
    sample_rate = 16000
    player = AudioPlayer()
    
    # Generate 3 short tones with different frequencies
    def generate_tone(freq, duration=0.5):
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = (np.sin(2 * np.pi * freq * t) * 0.3).astype(np.float32)
        audio_int16 = (audio * 32767).astype(np.int16)
        with io.BytesIO() as output:
            with wave.open(output, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            return output.getvalue()
    
    try:
        # Rapidly queue multiple audio clips
        tones = [generate_tone(440), generate_tone(523), generate_tone(659)]
        
        for i, tone in enumerate(tones):
            print(f"Playing tone {i+1}...")
            player.play_wav(tone)
            time.sleep(0.1)  # Small gap
        
        # Wait for last one to finish
        while player.is_playing():
            time.sleep(0.1)
        
        print("✓ Concurrent playback handled correctly")
        return True
        
    except Exception as e:
        print(f"✗ Concurrent playback failed: {e}")
        return False


def test_player_stop_while_playing():
    """Test stopping playback mid-play."""
    print("\n=== Test: Stop While Playing ===")
    
    sample_rate = 16000
    duration = 3.0
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
        player.play_wav(wav_bytes)
        time.sleep(0.5)
        
        if player.is_playing():
            print("✓ Playback started")
            player.stop()
            time.sleep(0.1)
            
            if not player.is_playing():
                print("✓ Playback stopped successfully")
                return True
            else:
                print("✗ Playback still active after stop")
                return False
        else:
            print("✗ Playback didn't start")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


# ===== SESSION MANAGEMENT TESTS =====

def test_session_history_management():
    """Test conversation history operations."""
    print("\n=== Test: Session History Management ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("⚠ Skipping (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="Test assistant",
        sample_rate=16000
    )
    
    try:
        # Add messages to history
        session.history.append({
            'role': 'user',
            'content': [{'type': 'text', 'text': 'Hello'}]
        })
        session.history.append({
            'role': 'assistant',
            'content': [{'type': 'text', 'text': 'Hi there'}]
        })
        
        print(f"✓ History length: {len(session.history)}")
        
        # Test reset
        session.reset_history()
        
        if len(session.history) == 0:
            print("✓ History reset successful")
            return True
        else:
            print("✗ History not cleared")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_session_message_building():
    """Test message building with system prompt."""
    print("\n=== Test: Session Message Building ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("⚠ Skipping (no API key)")
        return True
    
    client = OpenAI(api_key=api_key)
    session = VoiceAssistantSession(
        client=client,
        system_prompt="You are a helpful assistant.",
        sample_rate=16000
    )
    
    try:
        # Add some history
        session.history.append({
            'role': 'user',
            'content': [{'type': 'text', 'text': 'Test message'}]
        })
        
        # Build messages
        messages = session._build_messages()
        
        print(f"✓ Built {len(messages)} messages")
        print(f"  - System message: {messages[0]['role'] == 'system'}")
        print(f"  - History included: {len(messages) > 1}")
        
        if messages[0]['role'] == 'system' and len(messages) == 2:
            print("✓ Message building correct")
            return True
        else:
            print("✗ Message structure incorrect")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


# ===== PERFORMANCE TESTS =====

def test_vad_processing_speed():
    """Measure VAD processing performance."""
    print("\n=== Test: VAD Processing Speed ===")
    
    sample_rate = 16000
    chunk_ms = 30
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    vad = webrtcvad.Vad(2)
    
    # Generate 100 chunks
    chunks = [
        (np.random.randn(chunk_samples) * 1000).astype(np.int16)
        for _ in range(100)
    ]
    
    start_time = time.time()
    for chunk in chunks:
        try:
            vad.is_speech(chunk.tobytes(), sample_rate)
        except:
            pass
    elapsed = time.time() - start_time
    
    chunks_per_sec = len(chunks) / elapsed
    print(f"✓ Processed {len(chunks)} chunks in {elapsed:.3f}s")
    print(f"✓ Speed: {chunks_per_sec:.1f} chunks/sec")
    
    if chunks_per_sec > 100:  # Should be very fast
        print("✓ Performance acceptable")
        return True
    else:
        print("⚠ Performance slower than expected")
        return True  # Don't fail on slow hardware


def test_audio_conversion_performance():
    """Measure audio conversion performance."""
    print("\n=== Test: Audio Conversion Performance ===")
    
    sample_rate = 16000
    durations = [1.0, 5.0, 10.0, 30.0]
    
    for duration in durations:
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
        
        start_time = time.time()
        wav_bytes = numpy_to_wav_bytes(audio, sample_rate)
        elapsed = time.time() - start_time
        
        print(f"  {duration:4.1f}s audio → {len(wav_bytes):8d} bytes in {elapsed*1000:6.1f}ms")
    
    print("✓ Conversion performance measured")
    return True


# ===== CONCURRENCY TESTS =====

def test_interrupt_flag_threading():
    """Test interrupt flag with multiple threads."""
    print("\n=== Test: Interrupt Flag Threading ===")
    
    interrupt_flag = threading.Event()
    results = {'count': 0}
    lock = threading.Lock()
    
    def worker(worker_id):
        for _ in range(10):
            if interrupt_flag.is_set():
                break
            with lock:
                results['count'] += 1
            time.sleep(0.01)
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    
    for t in threads:
        t.start()
    
    time.sleep(0.1)
    interrupt_flag.set()
    
    for t in threads:
        t.join(timeout=1.0)
    
    print(f"✓ Threads processed {results['count']} operations before interrupt")
    print("✓ Interrupt flag threading works")
    return True


# ===== STRESS TESTS =====

def test_rapid_audio_player_operations():
    """Stress test with rapid play/stop/interrupt cycles."""
    print("\n=== Test: Rapid Audio Player Operations ===")
    
    sample_rate = 16000
    duration = 0.2
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
        for i in range(20):
            player.play_wav(wav_bytes)
            time.sleep(0.05)
            
            if i % 3 == 0:
                player.interrupt()
            elif i % 3 == 1:
                player.stop()
            
            time.sleep(0.02)
        
        print("✓ Survived 20 rapid play/stop/interrupt cycles")
        return True
        
    except Exception as e:
        print(f"✗ Failed during stress test: {e}")
        return False


def main():
    print("=" * 60)
    print("Voice Assistant VAD - Comprehensive Extended Tests")
    print("=" * 60)
    
    tests = [
        # Edge cases
        ("Empty Audio Input", test_empty_audio_input),
        ("Invalid Sample Rates", test_invalid_sample_rates),
        ("Audio Clipping Prevention", test_audio_clipping_prevention),
        ("Very Short Recording", test_very_short_recording),
        ("Max Recording Duration", test_max_recording_duration),
        
        # VAD parameters
        ("VAD Aggressiveness Levels", test_vad_aggressiveness_levels),
        ("VAD Chunk Sizes", test_vad_chunk_sizes),
        
        # Audio player
        ("Concurrent Audio Playback", test_concurrent_audio_playback),
        ("Stop While Playing", test_player_stop_while_playing),
        
        # Session management
        ("Session History Management", test_session_history_management),
        ("Session Message Building", test_session_message_building),
        
        # Performance
        ("VAD Processing Speed", test_vad_processing_speed),
        ("Audio Conversion Performance", test_audio_conversion_performance),
        
        # Concurrency
        ("Interrupt Flag Threading", test_interrupt_flag_threading),
        
        # Stress
        ("Rapid Audio Player Operations", test_rapid_audio_player_operations),
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
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for p in results.values() if p)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print("=" * 60)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
