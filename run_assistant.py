#!/usr/bin/env python3
"""
Quick start script for the ChatGPT-Style Voice Assistant.
Simply run: python3 run_assistant.py
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the voice assistant
from src.vad.voice_assistant_VAD import main

if __name__ == '__main__':
    print("=" * 60)
    print("Python Voice AI Agent")
    print("=" * 60)
    print()
    
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nSession ended.')
    except Exception as e:
        print(f'\n\n❌ Error: {e}')
        print('\nTroubleshooting:')
        print('1. Check your .env file has OPENAI_API_KEY')
        print('2. Ensure all dependencies are installed: pip install -r requirements.txt')
        print('3. Check microphone permissions')
        sys.exit(1)
