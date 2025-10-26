#!/usr/bin/env python3
"""
Unit tests for voice assistant functionality.
"""

import os
import sys
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI

def test_microphone_access():
    """Test if microphone is accessible."""
    print("\n=== Test 1: Microphone Access ===")
    try:
        # List audio devices
        devices = sd.query_devices()
        print(f"✓ Found {len(devices)} audio devices")
        
        # Get default input device
        default_input = sd.query_devices(kind='input')
        print(f"✓ Default input: {default_input['name']}")
        
        # Try to open a stream
        with sd.InputStream(samplerate=16000, channels=1, dtype='float32') as stream:
            data, _ = stream.read(1024)
            print(f"✓ Successfully read {len(data)} samples")
            rms = float(np.sqrt(np.mean(np.square(data))))
            print(f"✓ Current audio level (RMS): {rms:.4f}")
            
        return True
    except Exception as e:
        print(f"✗ Microphone test failed: {e}")
        return False

def test_audio_detection():
    """Test audio level detection with live monitoring."""
    print("\n=== Test 2: Audio Level Detection ===")
    print("Monitoring audio levels for 3 seconds...")
    print("(Try speaking to see if it's detected)")
    
    try:
        threshold = 0.03
        max_level = 0.0
        samples_above_threshold = 0
        total_samples = 0
        
        with sd.InputStream(samplerate=16000, channels=1, dtype='float32') as stream:
            for i in range(30):  # 3 seconds at ~100ms per read
                data, _ = stream.read(1024)
                rms = float(np.sqrt(np.mean(np.square(data))))
                max_level = max(max_level, rms)
                total_samples += 1
                
                if rms > threshold:
                    samples_above_threshold += 1
                    print(f"  [{i:2d}] RMS: {rms:.4f} *** ABOVE THRESHOLD ***")
                else:
                    print(f"  [{i:2d}] RMS: {rms:.4f}")
        
        print(f"\n✓ Max audio level detected: {max_level:.4f}")
        print(f"✓ Samples above threshold ({threshold}): {samples_above_threshold}/{total_samples}")
        
        if max_level < 0.001:
            print("⚠ Warning: Audio levels are extremely low. Microphone may be muted or not working.")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Audio detection test failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection."""
    print("\n=== Test 3: OpenAI API Connection ===")
    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("✗ OPENAI_API_KEY not found in .env file")
            return False
        
        print(f"✓ API key loaded (length: {len(api_key)})")
        
        client = OpenAI(api_key=api_key)
        
        # Test with a simple text completion
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'test successful' and nothing else."}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✓ API response: {result}")
        
        return True
    except Exception as e:
        print(f"✗ OpenAI connection test failed: {e}")
        return False

def test_audio_recording():
    """Test basic audio recording."""
    print("\n=== Test 4: Audio Recording ===")
    print("Recording 2 seconds of audio...")
    
    try:
        sample_rate = 16000
        duration = 2  # seconds
        
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
            audio_data = []
            for _ in range(int(sample_rate * duration / 1024)):
                data, _ = stream.read(1024)
                audio_data.append(data)
        
        audio = np.concatenate(audio_data, axis=0)
        print(f"✓ Recorded {len(audio)} samples ({len(audio)/sample_rate:.1f} seconds)")
        
        rms = float(np.sqrt(np.mean(np.square(audio))))
        print(f"✓ Average RMS: {rms:.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Audio recording test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Voice Assistant Functionality Tests")
    print("=" * 60)
    
    results = {
        "Microphone Access": test_microphone_access(),
        "Audio Detection": test_audio_detection(),
        "OpenAI Connection": test_openai_connection(),
        "Audio Recording": test_audio_recording()
    }
    
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
        print("✗ Some tests failed. Check output above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
