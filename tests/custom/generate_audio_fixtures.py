#!/usr/bin/env python3
"""
Generate audio fixtures for conversational flow testing.
Uses OpenAI's Text-to-Speech API to create realistic user audio files.
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()


# Customer database - maps verification codes to customer profiles
CUSTOMER_DATABASE = {
    "12345": {"name": "Michael", "property": "Charlotte's Street, Wynnum", "voice": "onyx"},
    "23456": {"name": "Sarah", "property": "Ocean Parade, Manly", "voice": "nova"},
    "34567": {"name": "David", "property": "River Road, Bulimba", "voice": "echo"},
    "45678": {"name": "Emily", "property": "Harbour View Terrace, Sydney", "voice": "shimmer"},
    "56789": {"name": "James", "property": "Mountain View Crescent, Brighton", "voice": "fable"},
}


def generate_user_audio_files():
    """Generate audio files for 5 different customers calling about their policies."""
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create audio fixtures directory
    audio_dir = Path(__file__).parent / "audio_fixtures"
    audio_dir.mkdir(exist_ok=True)
    
    # Generate audio for each customer
    for code, customer in CUSTOMER_DATABASE.items():
        customer_dir = audio_dir / f"customer_{code}"
        customer_dir.mkdir(exist_ok=True)
        
        # Define utterances for this customer
        user_utterances = {
            "01_greeting.wav": "Hello, I'd like to enquire about my current policy",
            "02_verification.wav": " ".join(code),  # Speak code with spaces between digits
            "03_request.wav": f"I need to increase the coverage on my {customer['property']} property to 1 million please",
            "04_confirm.wav": f"Yes, that's correct, the {customer['property']} property",
            "05_proceed.wav": "I've reviewed the document and I'd like to proceed",
            "06_thanks.wav": "No, that's all. Thank you",
        }
        
        print(f"\n{'='*70}")
        print(f"Customer: {customer['name']} (Code: {code}, Voice: {customer['voice']})")
        print(f"{'='*70}")
        
        for filename, text in user_utterances.items():
            output_path = customer_dir / filename
            
            if output_path.exists():
                print(f"✓ {filename:25s} - Already exists")
                continue
            
            try:
                # Generate speech using customer's voice
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=customer['voice'],
                    input=text,
                    response_format="wav"
                )
                
                response.write_to_file(output_path)
                file_size = output_path.stat().st_size / 1024
                print(f"✓ {filename:25s} - {file_size:6.1f} KB - '{text[:50]}...'")
                
            except Exception as e:
                print(f"✗ {filename:25s} - Error: {e}")
                continue
    
    print("\n" + "=" * 70)
    print(f"All audio fixtures saved to: {audio_dir}")
    print("=" * 70)
    
    # List all customer directories
    print("\nGenerated customer directories:")
    for customer_dir in sorted(audio_dir.glob("customer_*")):
        num_files = len(list(customer_dir.glob("*.wav")))
        print(f"  - {customer_dir.name:20s} ({num_files} audio files)")


def main():
    """Main entry point."""
    try:
        generate_user_audio_files()
        print("\n✅ Audio fixture generation complete!")
        print("\nYou can now run the conversational flow test:")
        print("  python3 -m tests.custom.test_update_policy_conversational_flow")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. OPENAI_API_KEY is set in .env")
        print("  2. You have OpenAI API access")
        sys.exit(1)


if __name__ == '__main__':
    main()
