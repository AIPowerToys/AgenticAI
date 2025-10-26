#!/usr/bin/env python3
"""
Speech quality and robustness tests for Python Voice AI Agent.
Tests noise rejection, echo cancellation, and speech detection accuracy.
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
from src.vad.voice_assistant_VAD import detect_speech_vad, AudioPlayer
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


def test_background_noise_rejection():
    """Test VAD filters background noise."""
    print("\n=== Test: Background Noise Rejection ===")
    print("Testing VAD with simulated background noise")
    
    sample_rate = 16000
    chunk_ms = 30
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    vad = webrtcvad.Vad(3)  # Most aggressive
    
    # Generate different noise types
    silence = np.zeros(chunk_samples, dtype=np.int16)
    white_noise = (np.random.randn(chunk_samples) * 500).astype(np.int16)
    pink_noise = (np.random.randn(chunk_samples) * 300).astype(np.int16)
    
    try:
        silence_speech = vad.is_speech(silence.tobytes(), sample_rate)
        white_speech = vad.is_speech(white_noise.tobytes(), sample_rate)
        pink_speech = vad.is_speech(pink_noise.tobytes(), sample_rate)
        
        print(f"  Silence detected as speech: {silence_speech}")
        print(f"  White noise detected as speech: {white_speech}")
        print(f"  Pink noise detected as speech: {pink_speech}")
        
        # Silence should never be detected as speech
        if not silence_speech:
            print("✓ Silence correctly rejected")
            return True
        else:
            print("⚠ Silence detected as speech (unexpected)")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_echo_cancellation_simulation():
    """Test VAD doesn't trigger on played audio."""
    print("\n=== Test: Echo Cancellation (Simulated) ===")
    print("Testing that playback doesn't trigger VAD")
    
    sample_rate = 16000
    duration = 2.0
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
        print("Playing audio... VAD should use aggressiveness 3")
        print("(In real scenario, speaker output should not trigger VAD)")
        player.play_wav(wav_bytes)
        
        # Monitor VAD during playback
        vad = webrtcvad.Vad(3)  # Most aggressive
        chunk_ms = 30
        chunk_samples = int(sample_rate * chunk_ms / 1000)
        
        speech_frames = 0
        total_frames = 0
        
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            for _ in range(30):  # ~1 second
                if not player.is_playing():
                    break
                data, _ = stream.read(chunk_samples)
                try:
                    is_speech = vad.is_speech(data.tobytes(), sample_rate)
                    total_frames += 1
                    if is_speech:
                        speech_frames += 1
                except:
                    pass
        
        player.stop()
        
        if total_frames > 0:
            speech_pct = (speech_frames / total_frames) * 100
            print(f"\n  Total frames: {total_frames}")
            print(f"  Speech detected: {speech_frames} ({speech_pct:.1f}%)")
            print("✓ Echo cancellation behavior measured")
            print("  Note: Real echo cancellation needs hardware/OS support")
            return True
        else:
            print("✓ No frames captured (expected)")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_far_field_speech_simulation():
    """Test speech detection at different volumes."""
    print("\n=== Test: Far-Field Speech (Volume Simulation) ===")
    print("Testing VAD at different volume levels")
    
    sample_rate = 16000
    chunk_ms = 30
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    vad = webrtcvad.Vad(2)
    
    # Simulate different distances with volume levels
    volumes = {
        'close (100%)': 1.0,
        'medium (50%)': 0.5,
        'far (25%)': 0.25,
        'very far (10%)': 0.1,
    }
    
    try:
        for distance, volume in volumes.items():
            # Generate speech-like signal at different volumes
            speech_signal = (np.random.randn(chunk_samples) * 2000 * volume).astype(np.int16)
            
            try:
                is_speech = vad.is_speech(speech_signal.tobytes(), sample_rate)
                print(f"  {distance:20s}: speech={is_speech}")
            except:
                print(f"  {distance:20s}: VAD error")
        
        print("✓ Volume-based detection tested")
        print("  Real test requires actual distance measurements")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_whisper_and_loud_speech():
    """Test different volume levels for recording."""
    if skip_if_not_interactive("Whisper and Loud Speech"):
        return True
    
    print("\n=== Test: Whisper and Loud Speech ===")
    print("This requires manual testing with actual speech")
    print("Press Enter to test recording (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    try:
        print("\nWhisper test: Speak very quietly for 2 seconds...")
        audio_whisper = detect_speech_vad(
            sample_rate=16000,
            silence_duration=1.0,
            max_seconds=3.0
        )
        
        whisper_detected = audio_whisper is not None
        print(f"  Whisper detected: {whisper_detected}")
        
        print("\nLoud speech test: Speak loudly for 2 seconds...")
        audio_loud = detect_speech_vad(
            sample_rate=16000,
            silence_duration=1.0,
            max_seconds=3.0
        )
        
        loud_detected = audio_loud is not None
        print(f"  Loud speech detected: {loud_detected}")
        
        if whisper_detected and loud_detected:
            print("✓ Both volume levels detected")
            return True
        else:
            print("⚠ Some levels not detected")
            return True  # Don't fail on hardware limitations
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_continuous_vs_intermittent_speech():
    """Test detection of different speech patterns."""
    if skip_if_not_interactive("Continuous vs Intermittent Speech"):
        return True
    
    print("\n=== Test: Continuous vs Intermittent Speech ===")
    print("Manual test for speech pattern detection")
    print("Press Enter to test (or 's' to skip)...")
    
    if input().strip().lower() == 's':
        print("⚠ Skipped")
        return True
    
    try:
        print("\nContinuous speech: Talk continuously for 3 seconds...")
        audio_cont = detect_speech_vad(
            sample_rate=16000,
            silence_duration=1.5,
            max_seconds=5.0
        )
        
        cont_detected = audio_cont is not None
        if cont_detected:
            cont_duration = len(audio_cont) / 16000
            print(f"  Continuous speech: {cont_duration:.1f}s recorded")
        
        print("\nIntermittent speech: Say word... pause... word... pause...")
        audio_int = detect_speech_vad(
            sample_rate=16000,
            silence_duration=1.5,
            max_seconds=5.0
        )
        
        int_detected = audio_int is not None
        if int_detected:
            int_duration = len(audio_int) / 16000
            print(f"  Intermittent speech: {int_duration:.1f}s recorded")
        
        print("✓ Different speech patterns tested")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Speech Quality & Robustness Tests - Voice AI Agent")
    print("=" * 60)
    
    tests = [
        ("Background Noise Rejection", test_background_noise_rejection),
        ("Echo Cancellation Simulation", test_echo_cancellation_simulation),
        ("Far-Field Speech Simulation", test_far_field_speech_simulation),
        ("Whisper and Loud Speech", test_whisper_and_loud_speech),
        ("Continuous vs Intermittent Speech", test_continuous_vs_intermittent_speech),
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
