#!/usr/bin/env python3
"""
Standalone test script for voice assistant functionality.
Tests: recording, transcription, GPT-4o audio response, playback, history retention.
"""

import os
import sys
import base64
import io
import threading
import time
import wave
from typing import List, Dict, Optional

import numpy as np
import simpleaudio as sa
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI


class AudioPlayer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._play_obj: Optional[sa.PlayObject] = None
        self._interrupt = threading.Event()

    def play_wav(self, wav_bytes: bytes) -> None:
        with self._lock:
            if self._play_obj is not None:
                self._play_obj.stop()
                self._play_obj = None
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
            self._play_obj = sa.play_buffer(frames, channels, sample_width, sample_rate)

    def is_playing(self) -> bool:
        with self._lock:
            return self._play_obj is not None and self._play_obj.is_playing()

    def wait_finish(self) -> None:
        """Wait for current playback to complete, checking for interrupts."""
        while True:
            with self._lock:
                if self._play_obj is None or not self._play_obj.is_playing():
                    break
            if self._interrupt.is_set():
                self.stop()
                self._interrupt.clear()
                return  # Exit immediately on interrupt
            time.sleep(0.05)  # Check more frequently
        self._interrupt.clear()

    def interrupt(self) -> None:
        """Signal to interrupt playback."""
        self._interrupt.set()

    def stop(self) -> None:
        with self._lock:
            if self._play_obj is not None:
                self._play_obj.stop()
                self._play_obj = None


def record_until_silence(
    sample_rate: int = 16000,
    threshold: float = 0.02,
    silence_duration: float = 1.5,
    max_seconds: float = 30.0,
    chunk_size: int = 1024,
    interrupt_flag: Optional[threading.Event] = None
) -> Optional[np.ndarray]:
    """Record audio until silence is detected or interrupted."""
    buffer: List[np.ndarray] = []
    speaking = False
    silence_start: Optional[float] = None
    start_time = time.time()
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        while True:
            if interrupt_flag and interrupt_flag.is_set():
                break
            data, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(np.square(data))))
            now = time.time()
            if rms > threshold:
                if not speaking:
                    print('Speech detected...')
                speaking = True
                silence_start = None
                buffer.append(data.copy())
            else:
                if speaking:
                    buffer.append(data.copy())
                    if silence_start is None:
                        silence_start = now
                    elif now - silence_start >= silence_duration:
                        break
            if now - start_time >= max_seconds:
                break
    # Stream closed here, ensure clean shutdown
    time.sleep(0.1)
    if not buffer:
        return None
    return np.concatenate(buffer, axis=0)

def monitor_for_interruption(
    interrupt_flag: threading.Event,
    sample_rate: int = 16000,
    interrupt_threshold: float = 0.05,  # Very high - only very loud/close speech
    chunk_size: int = 1024
) -> None:
    """Monitor for loud speech that indicates user interruption."""
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        consecutive_loud = 0
        max_seen = 0.0
        while not interrupt_flag.is_set():
            try:
                data, _ = stream.read(chunk_size)
                rms = float(np.sqrt(np.mean(np.square(data))))
                max_seen = max(max_seen, rms)
                # Need 8 consecutive loud frames to avoid false triggers from speaker
                if rms > interrupt_threshold:
                    consecutive_loud += 1
                    if consecutive_loud >= 8:
                        print(f'\n[Interruption detected - RMS: {rms:.4f}, Max: {max_seen:.4f}]')
                        interrupt_flag.set()
                        break
                else:
                    consecutive_loud = 0
            except Exception:
                break


def numpy_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio = np.clip(audio, -1.0, 1.0)
    int_audio = (audio * 32767).astype(np.int16)
    with io.BytesIO() as output:
        with wave.open(output, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(int_audio.tobytes())
        return output.getvalue()


class VoiceAssistantSession:
    def __init__(
        self,
        client: OpenAI,
        system_prompt: str,
        sample_rate: int = 16000,
        threshold: float = 0.01,
        silence_duration: float = 1.0,
        max_seconds: float = 30.0,
        interrupt_threshold: float = 0.08
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.max_seconds = max_seconds
        self.interrupt_threshold = interrupt_threshold
        self.history: List[Dict[str, List[Dict[str, str]]]] = []
        self.player = AudioPlayer()
        self.is_responding = False
        self.interrupt_flag = threading.Event()

    def stop_playback(self) -> None:
        self.player.stop()

    def reset_history(self) -> None:
        self.history.clear()
        print('Conversation history cleared.')

    def _build_messages(self) -> List[Dict[str, List[Dict[str, str]]]]:
        return [
            {
                'role': 'system',
                'content': [{ 'type': 'text', 'text': self.system_prompt }]
            }
        ] + self.history

    def record_user(self) -> Optional[str]:
        # Don't start new recording while AI is responding
        if self.is_responding:
            return None
        
        self.interrupt_flag.clear()
        audio = record_until_silence(
            sample_rate=self.sample_rate,
            threshold=self.threshold,
            silence_duration=self.silence_duration,
            max_seconds=self.max_seconds,
            interrupt_flag=self.interrupt_flag
        )
        if audio is None:
            return None
        wav_bytes = numpy_to_wav_bytes(audio, self.sample_rate)
        transcription = self.client.audio.transcriptions.create(
            model='whisper-1',
            file=('user.wav', wav_bytes, 'audio/wav')
        )
        user_text = transcription.text.strip()
        if not user_text:
            print('Transcription failed to capture speech.')
            return None
        print(f'You: {user_text}')
        self.history.append({
            'role': 'user',
            'content': [{ 'type': 'text', 'text': user_text }]
        })
        return user_text

    def respond(self) -> None:
        self.is_responding = True
        self.interrupt_flag.clear()
        
        # Start interrupt monitor
        monitor_thread = threading.Thread(
            target=monitor_for_interruption,
            args=(self.interrupt_flag, self.sample_rate, self.interrupt_threshold),
            daemon=True
        )
        
        try:
            response = self.client.chat.completions.create(
                model='gpt-4o-audio-preview',
                modalities=['text', 'audio'],
                audio={'voice': 'alloy', 'format': 'wav'},
                messages=[msg for msg in self._build_messages()]
            )
            message = response.choices[0].message
            assistant_text = message.content or ''
            audio_bytes = None
            if hasattr(message, 'audio') and message.audio:
                audio_bytes = base64.b64decode(message.audio.data)
            if assistant_text:
                print(f'\nAssistant: {assistant_text}')
                self.history.append({
                    'role': 'assistant',
                    'content': [{ 'type': 'text', 'text': assistant_text }]
                })
            if audio_bytes:
                # Start playback first
                self.player.play_wav(audio_bytes)
                # Small delay to let playback start before monitoring
                time.sleep(0.2)
                # Now start monitoring for interruptions
                monitor_thread.start()
                # Wait for audio to finish OR interruption
                self.player.wait_finish()
                # Stop interrupt monitor
                was_interrupted = self.interrupt_flag.is_set()
                self.interrupt_flag.set()
                monitor_thread.join(timeout=0.5)
                
                # If interrupted, immediately resume listening
                if was_interrupted:
                    print('\n🎤 Listening...')
                    return
                
                # Otherwise, small delay before listening again
                time.sleep(0.3)
        except Exception as e:
            print(f'\n⚠ Error getting response: {e}')
            # Remove the failed user message from history
            if self.history and self.history[-1]['role'] == 'user':
                self.history.pop()
        finally:
            self.is_responding = False
            self.interrupt_flag.clear()

    def turn(self) -> None:
        if self.record_user() is None:
            return
        self.respond()


def continuous_listener(session: VoiceAssistantSession, stop_flag: threading.Event):
    """Background thread for continuous listening."""
    print('\n🎤 Listening continuously... Just start speaking!')
    print('(Microphone pauses during AI responses)\n')
    
    while not stop_flag.is_set():
        try:
            if not session.is_responding:
                user_text = session.record_user()
                if user_text:
                    print(f'\nYou: {user_text}')
                    session.respond()
                    print('\n🎤 Listening...')
            else:
                time.sleep(0.1)
        except Exception as e:
            print(f'\n⚠ Listener error: {e}')
            time.sleep(1)

def main():
    # Load environment
    load_dotenv()
    
    SYSTEM_PROMPT = os.getenv("SYTEM_PROMPT", "You are an ai voice assistance")
    API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not API_KEY:
        raise ValueError("Set OPENAI_API_KEY in your .env file before proceeding.")
    
    client = OpenAI(api_key=API_KEY)
    print("Client configured. System prompt loaded.")
    
    # Initialize session
    assistant_session = VoiceAssistantSession(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        sample_rate=16000,
        threshold=0.008,  # Lower threshold for quieter mics
        silence_duration=1.5,
        max_seconds=30.0,
        interrupt_threshold=0.05  # Very high - only extremely loud/close speech
    )
    print('Voice assistant session ready.')
    print('\n=== Continuous Conversation Mode ===')
    print('Just start speaking - no Enter key needed!')
    print('Speak VERY LOUD to interrupt AI mid-response')
    print('Type "q" + Enter: Quit')
    print('Type "r" + Enter: Reset conversation history')
    
    stop_flag = threading.Event()
    listener_thread = threading.Thread(
        target=continuous_listener,
        args=(assistant_session, stop_flag),
        daemon=True
    )
    listener_thread.start()
    
    # Command loop for quit/reset
    while True:
        try:
            command = input().strip().lower()
            if command == 'q':
                stop_flag.set()
                assistant_session.stop_playback()
                print('\nSession ended.')
                break
            elif command == 'r':
                assistant_session.reset_history()
                print('\n✓ Conversation reset\n🎤 Listening...')
        except EOFError:
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nSession ended.')
