#!/usr/bin/env python3
"""
Comprehensive end-to-end tests for VAD-based voice assistant.
Tests interruption, speech detection, and full conversation flow.
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
    VoiceAssistantSession
)
import threading


def test_vad_speech_detection():
    """Test WebRTC VAD can detect human speech vs noise."""
    print("\n=== Test 1: VAD Speech Detection ===")
    
    vad = webrtcvad.Vad(2)  # Medium aggressiveness
    sample_rate = 16000
    chunk_ms = 30
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    
    print(f"Monitoring for 3 seconds. Try speaking vs staying silent.")
    print("Collecting audio samples...")
    
    speech_frames = 0
    non_speech_frames = 0
    total_frames = 0
    
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
        for i in range(100):  # ~3 seconds
            data, _ = stream.read(chunk_samples)
            audio_bytes = data.tobytes()
            
            try:
                is_speech = vad.is_speech(audio_bytes, sample_rate)
                total_frames += 1
                
                if is_speech:
                    speech_frames += 1
                    print(f"  [{i:3d}] SPEECH DETECTED")
                else:
                    non_speech_frames += 1
                    print(f"  [{i:3d}] No speech")
            except Exception as e:
                print(f"  [{i:3d}] VAD error: {e}")
    
    print(f"\n✓ Total frames: {total_frames}")
    print(f"✓ Speech frames: {speech_frames} ({speech_frames/total_frames*100:.1f}%)")
    print(f"✓ Non-speech frames: {non_speech_frames} ({non_speech_frames/total_frames*100:.1f}%)")
    
    if total_frames > 0:
        print("✓ VAD is working")
        return True
    return False


def test_audio_player_interruption():
    """Test AudioPlayer interruption mechanism."""
    print("\n=== Test 2: Audio Player Interruption ===")
    
    # Generate a 3-second test tone
    sample_rate = 16000
    duration = 3.0
    frequency = 440  # A4 note
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 0.3).astype(np.float32)
    
    # Convert to WAV bytes
    import io
    import wave
    audio_int16 = (audio * 32767).astype(np.int16)
    with io.BytesIO() as output:
        with wave.open(output, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        wav_bytes = output.getvalue()
    
    player = AudioPlayer()
    
    print("Playing 3-second tone. Will interrupt after 1 second...")
    player.play_wav(wav_bytes)
    
    # Wait 1 second then interrupt
    time.sleep(1.0)
    print("Interrupting playback...")
    player.interrupt()
    
    # Check if interruption worked
    was_interrupted = player.wait_finish_or_interrupt()
    
    if was_interrupted:
        print("✓ Interruption successful - playback stopped immediately")
        return True
    else:
        print("✗ Interruption failed - playback completed normally")
        return False


def test_vad_interruption_monitor():
    """Test VAD-based interruption detection during playback."""
    print("\n=== Test 3: VAD Interruption Monitor ===")
    
    # Generate a 5-second test tone
    sample_rate = 16000
    duration = 5.0
    frequency = 440
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 0.3).astype(np.float32)
    
    import io
    import wave
    audio_int16 = (audio * 32767).astype(np.int16)
    with io.BytesIO() as output:
        with wave.open(output, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        wav_bytes = output.getvalue()
    
    player = AudioPlayer()
    interrupt_flag = threading.Event()
    
    print("Playing 5-second tone...")
    print("SPEAK NOW to test interruption detection!")
    print("(The monitor should detect your speech and stop playback)")
    
    player.play_wav(wav_bytes)
    time.sleep(0.2)  # Let playback start
    
    # Start interruption monitor
    monitor_thread = threading.Thread(
        target=monitor_for_speech_interruption,
        args=(interrupt_flag, player, sample_rate),
        daemon=True
    )
    monitor_thread.start()
    
    # Wait for playback to complete or interruption
    was_interrupted = player.wait_finish_or_interrupt()
    
    # Stop monitor
    interrupt_flag.set()
    monitor_thread.join(timeout=1.0)
    
    if was_interrupted:
        print("✓ Interruption detected via VAD - you spoke during playback")
        return True
    else:
        print("✓ Playback completed without interruption - you stayed silent")
        return True


def test_openai_integration():
    """Test OpenAI API connection and audio response."""
    print("\n=== Test 4: OpenAI Audio Response ===")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("✗ OPENAI_API_KEY not found")
        return False
    
    client = OpenAI(api_key=api_key)
    
    try:
        print("Requesting audio response from OpenAI...")
        response = client.chat.completions.create(
            model='gpt-4o-audio-preview',
            modalities=['text', 'audio'],
            audio={'voice': 'alloy', 'format': 'wav'},
            messages=[
                {
                    'role': 'user',
                    'content': [{'type': 'text', 'text': 'Say "test successful" in a cheerful voice.'}]
                }
            ]
        )
        
        message = response.choices[0].message
        assistant_text = message.content or ''
        
        print(f"✓ Text response: {assistant_text}")
        
        if hasattr(message, 'audio') and message.audio:
            import base64
            audio_bytes = base64.b64decode(message.audio.data)
            print(f"✓ Received audio response ({len(audio_bytes)} bytes)")
            
            # Test playback
            player = AudioPlayer()
            print("Playing audio response...")
            player.play_wav(audio_bytes)
            player.wait_finish_or_interrupt()
            
            print("✓ Audio playback successful")
            return True
        else:
            print("✗ No audio in response")
            return False
            
    except Exception as e:
        print(f"✗ OpenAI API error: {e}")
        return False


def test_full_conversation_flow():
    """Test complete conversation flow with real recording."""
    print("\n=== Test 5: Full Conversation Flow ===")
    print("This test will:")
    print("1. Record your speech using VAD")
    print("2. Transcribe it with Whisper")
    print("3. Get GPT-4o audio response")
    print("4. Play the response")
    print("\nPress Enter when ready to speak...")
    input()
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("✗ OPENAI_API_KEY not found")
        return False
    
    client = OpenAI(api_key=api_key)
    
    try:
        # 1. Record speech
        print("\n🎤 Listening... speak now!")
        audio = detect_speech_vad(
            sample_rate=16000,
            silence_duration=1.5,
            max_seconds=10.0
        )
        
        if audio is None:
            print("✗ No speech detected")
            return False
        
        print(f"✓ Recorded {len(audio)} samples")
        
        # 2. Transcribe
        from src.vad.voice_assistant_VAD import numpy_to_wav_bytes
        wav_bytes = numpy_to_wav_bytes(audio, 16000)
        
        print("Transcribing...")
        transcription = client.audio.transcriptions.create(
            model='whisper-1',
            file=('user.wav', wav_bytes, 'audio/wav')
        )
        user_text = transcription.text.strip()
        print(f"✓ You said: {user_text}")
        
        # 3. Get AI response
        print("Getting AI response...")
        response = client.chat.completions.create(
            model='gpt-4o-audio-preview',
            modalities=['text', 'audio'],
            audio={'voice': 'alloy', 'format': 'wav'},
            messages=[
                {
                    'role': 'user',
                    'content': [{'type': 'text', 'text': user_text}]
                }
            ]
        )
        
        message = response.choices[0].message
        assistant_text = message.content or ''
        print(f"✓ AI response: {assistant_text}")
        
        # 4. Play response
        if hasattr(message, 'audio') and message.audio:
            import base64
            audio_bytes = base64.b64decode(message.audio.data)
            
            player = AudioPlayer()
            print("Playing response...")
            player.play_wav(audio_bytes)
            player.wait_finish_or_interrupt()
            
            print("✓ Full conversation flow successful!")
            return True
        else:
            print("✗ No audio in response")
            return False
            
    except Exception as e:
        print(f"✗ Conversation flow error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Voice Assistant VAD - End-to-End Tests")
    print("=" * 60)
    
    tests = [
        ("VAD Speech Detection", test_vad_speech_detection),
        ("Audio Player Interruption", test_audio_player_interruption),
        ("VAD Interruption Monitor", test_vad_interruption_monitor),
        ("OpenAI Integration", test_openai_integration),
        ("Full Conversation Flow", test_full_conversation_flow)
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
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
