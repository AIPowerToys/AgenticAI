#!/usr/bin/env python3
"""
Voice Assistant with proper Voice Activity Detection (VAD) - ChatGPT-style.
Uses WebRTC VAD to distinguish human speech from speaker playback.
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
import webrtcvad
from dotenv import load_dotenv
from openai import OpenAI


class AudioPlayer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._play_obj: Optional[sa.PlayObject] = None
        self._is_playing = False
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
            self._is_playing = True
            self._interrupt.clear()

    def is_playing(self) -> bool:
        with self._lock:
            if self._play_obj is None:
                return False
            if not self._play_obj.is_playing():
                self._is_playing = False
                return False
            return self._is_playing

    def wait_finish_or_interrupt(self) -> bool:
        """Wait for playback to complete OR interruption. Returns True if interrupted."""
        while self.is_playing():
            if self._interrupt.is_set():
                self.stop()
                return True
            time.sleep(0.05)
        return False

    def interrupt(self) -> None:
        """Signal to interrupt playback."""
        self._interrupt.set()

    def stop(self) -> None:
        with self._lock:
            if self._play_obj is not None:
                self._play_obj.stop()
                self._play_obj = None
            self._is_playing = False


def monitor_for_speech_interruption(
    interrupt_flag: threading.Event,
    player: AudioPlayer,
    sample_rate: int = 16000,
    chunk_ms: int = 30
) -> None:
    """Monitor for human speech using VAD during playback to detect interruptions."""
    vad = webrtcvad.Vad(3)  # Aggressiveness 3 (most aggressive - only clear speech)
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    consecutive_speech = 0
    
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
        while player.is_playing() and not interrupt_flag.is_set():
            try:
                data, _ = stream.read(chunk_samples)
                audio_bytes = data.tobytes()
                
                try:
                    is_speech = vad.is_speech(audio_bytes, sample_rate)
                except Exception:
                    is_speech = False
                
                if is_speech:
                    consecutive_speech += 1
                    # Need 3 consecutive speech frames (~90ms) to confirm interruption
                    if consecutive_speech >= 3:
                        print('\n[Interruption detected - you spoke]')
                        player.interrupt()
                        interrupt_flag.set()
                        break
                else:
                    consecutive_speech = 0
            except Exception:
                break


def detect_speech_vad(
    sample_rate: int = 16000,
    silence_duration: float = 1.5,
    max_seconds: float = 30.0,
    chunk_ms: int = 30  # WebRTC VAD requires 10, 20, or 30ms chunks
) -> Optional[np.ndarray]:
    """
    Record audio using WebRTC VAD to detect human speech.
    VAD distinguishes speech patterns from other audio.
    """
    vad = webrtcvad.Vad(2)  # Aggressiveness 2 (0-3, higher = stricter)
    
    chunk_samples = int(sample_rate * chunk_ms / 1000)
    buffer: List[np.ndarray] = []
    speaking = False
    silence_start: Optional[float] = None
    start_time = time.time()
    
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
        while True:
            data, _ = stream.read(chunk_samples)
            now = time.time()
            
            # Convert to bytes for VAD
            audio_bytes = data.tobytes()
            
            # VAD returns True if speech detected
            try:
                is_speech = vad.is_speech(audio_bytes, sample_rate)
            except Exception:
                is_speech = False
            
            if is_speech:
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
    
    time.sleep(0.1)
    if not buffer:
        return None
    
    # Convert back to float32 for processing
    audio_int16 = np.concatenate(buffer, axis=0)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    return audio_float32


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
        silence_duration: float = 1.5,
        max_seconds: float = 30.0
    ) -> None:
        self.client = client
        self.system_prompt = system_prompt
        self.sample_rate = sample_rate
        self.silence_duration = silence_duration
        self.max_seconds = max_seconds
        self.history: List[Dict[str, List[Dict[str, str]]]] = []
        self.player = AudioPlayer()
        self.is_responding = False

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
        # Don't record while AI is responding
        if self.is_responding:
            return None
        
        audio = detect_speech_vad(
            sample_rate=self.sample_rate,
            silence_duration=self.silence_duration,
            max_seconds=self.max_seconds
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
        interrupt_flag = threading.Event()
        
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
                # Start playback
                self.player.play_wav(audio_bytes)
                # Small delay before monitoring starts
                time.sleep(0.2)
                
                # Start VAD-based interruption monitor
                monitor_thread = threading.Thread(
                    target=monitor_for_speech_interruption,
                    args=(interrupt_flag, self.player, self.sample_rate),
                    daemon=True
                )
                monitor_thread.start()
                
                # Wait for playback to complete OR interruption
                was_interrupted = self.player.wait_finish_or_interrupt()
                
                # Stop monitor
                interrupt_flag.set()
                monitor_thread.join(timeout=0.5)
                
                if was_interrupted:
                    print('🎤 Listening...')
                    return
                
                # Small delay before listening again
                time.sleep(0.3)
        
        except Exception as e:
            print(f'\n⚠ Error getting response: {e}')
            # Remove failed user message from history
            if self.history and self.history[-1]['role'] == 'user':
                self.history.pop()
        
        finally:
            self.is_responding = False

    def turn(self) -> None:
        if self.record_user() is None:
            return
        self.respond()


def continuous_listener(session: VoiceAssistantSession, stop_flag: threading.Event):
    """Background thread for continuous listening."""
    print('\n🎤 Listening continuously... Just start speaking!')
    print('(VAD detects human speech, ignores speaker audio)\n')
    
    while not stop_flag.is_set():
        try:
            if not session.is_responding:
                user_text = session.record_user()
                if user_text:
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
        silence_duration=1.5,
        max_seconds=30.0
    )
    print('Voice assistant session ready.')
    print('\n=== VAD-Based Continuous Conversation ===')
    print('✓ Uses WebRTC Voice Activity Detection')
    print('✓ Automatically ignores speaker playback')
    print('✓ Start speaking anytime to interrupt AI')
    print('\nType "q" + Enter: Quit')
    print('Type "r" + Enter: Reset conversation history')
    
    stop_flag = threading.Event()
    listener_thread = threading.Thread(
        target=continuous_listener,
        args=(assistant_session, stop_flag),
        daemon=True
    )
    listener_thread.start()
    
    # Command loop
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
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nSession ended.')
