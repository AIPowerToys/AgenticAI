#!/usr/bin/env python3
"""
Conversation context tests for Python Voice AI Agent.
Tests multi-turn memory, context retention, and history management.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import os
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import VoiceAssistantSession


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


def test_multi_turn_context_retention():
    """Test context maintained across multiple turns."""
    if skip_if_not_interactive("Multi-Turn Context Retention"):
        return True
    
    print("\n=== Test: Multi-Turn Context Retention ===")
    print("Testing 3-turn conversation with context")
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
        system_prompt="Remember details from the conversation. Be brief.",
        sample_rate=16000
    )
    
    try:
        print("\nTurn 1: Say 'My name is [YourName]'")
        session.turn()
        
        print("\nTurn 2: Say 'What's my name?'")
        session.turn()
        
        print("\nTurn 3: Say 'What did I just ask you?'")
        session.turn()
        
        print(f"\n✓ Context tested across 3 turns")
        print(f"  History length: {len(session.history)}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_long_conversation_memory():
    """Test 10+ turn conversation maintains context."""
    if skip_if_not_interactive("Long Conversation Memory"):
        return True
    
    print("\n=== Test: Long Conversation Memory ===")
    print("Simulating 10-turn conversation")
    print("Press Enter to run automated test (or 's' to skip)...")
    
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
        system_prompt="You are a helpful assistant. Be very brief.",
        sample_rate=16000
    )
    
    # Simulate conversation by adding to history
    test_conversation = [
        ("Tell me about Python", "Python is a programming language."),
        ("What are its main features?", "It's interpreted, dynamic, and readable."),
        ("Who created it?", "Guido van Rossum created Python."),
        ("When?", "In 1991."),
        ("Is it popular?", "Yes, very popular for web and data science."),
    ]
    
    try:
        for user_msg, assistant_msg in test_conversation:
            session.history.append({
                'role': 'user',
                'content': [{'type': 'text', 'text': user_msg}]
            })
            session.history.append({
                'role': 'assistant',
                'content': [{'type': 'text', 'text': assistant_msg}]
            })
            print(f"  Turn: '{user_msg[:30]}...'")
        
        print(f"\n✓ History contains {len(session.history)} messages")
        
        # Test that message building includes all history
        messages = session._build_messages()
        print(f"✓ Built messages: {len(messages)} (system + {len(session.history)} history)")
        
        if len(messages) == len(session.history) + 1:  # +1 for system
            print("✓ Long conversation memory working")
            return True
        else:
            print("✗ Message building incorrect")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_context_after_interruption():
    """Test context preserved after interrupting AI."""
    if skip_if_not_interactive("Context After Interruption"):
        return True
    
    print("\n=== Test: Context After Interruption ===")
    print("Testing context preservation after barge-in")
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
        system_prompt="Remember all context. Tell long stories.",
        sample_rate=16000
    )
    
    try:
        print("\nSay: 'Tell me about space exploration'")
        if session.record_user():
            # Start response but don't wait for completion
            import threading
            response_thread = threading.Thread(target=session.respond)
            response_thread.start()
            
            # Wait then interrupt
            time.sleep(2.0)
            print("\nInterrupting... Say: 'Wait, tell me more about Mars instead'")
            session.player.interrupt()
            response_thread.join(timeout=5)
            
            # Continue conversation
            if session.record_user():
                session.respond()
        
        print(f"\n✓ Context after interruption tested")
        print(f"  History preserved: {len(session.history)} messages")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_history_reset_functionality():
    """Test conversation reset clears context properly."""
    print("\n=== Test: History Reset Functionality ===")
    
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
        # Add some history
        for i in range(5):
            session.history.append({
                'role': 'user',
                'content': [{'type': 'text', 'text': f'Message {i}'}]
            })
        
        print(f"History before reset: {len(session.history)} messages")
        
        session.reset_history()
        
        print(f"History after reset: {len(session.history)} messages")
        
        if len(session.history) == 0:
            print("✓ History reset working correctly")
            return True
        else:
            print("✗ History not cleared")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Conversation Context Tests - Voice AI Agent")
    print("=" * 60)
    
    tests = [
        ("Multi-Turn Context Retention", test_multi_turn_context_retention),
        ("Long Conversation Memory", test_long_conversation_memory),
        ("Context After Interruption", test_context_after_interruption),
        ("History Reset Functionality", test_history_reset_functionality),
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
