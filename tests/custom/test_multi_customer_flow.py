#\!/usr/bin/env python3
"""
Multi-Customer Conversational Flow Test

Tests PRODUCTION-REALISTIC conversational flows with 5 different customers.

KEY FEATURES:
- Pre-recorded CUSTOMER audio (simulating real callers)  
- Real-time AI AUDIO generation (via OpenAI TTS API)
- Dynamic context switching based on verification codes
- Tests 5 different customers with unique properties

This mimics a real production environment where different customers call in
and the AI responds with dynamically generated audio.
"""

import sys
import os
from pathlib import Path
import time
import wave
import base64

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from openai import OpenAI
from src.vad.voice_assistant_VAD import AudioPlayer, numpy_to_wav_bytes
import numpy as np

load_dotenv()


# Customer database - maps verification codes to customer profiles
CUSTOMER_DATABASE = {
    "12345": {
        "name": "Michael",
        "property": "Charlotte's Street, Wynnum",
        "coverage": "$800,000",
        "new_coverage": "$1,000,000"
    },
    "23456": {
        "name": "Sarah",  
        "property": "Ocean Parade, Manly",
        "coverage": "$650,000",
        "new_coverage": "$900,000"
    },
    "34567": {
        "name": "David",
        "property": "River Road, Bulimba",
        "coverage": "$550,000",
        "new_coverage": "$750,000"
    },
    "45678": {
        "name": "Emily",
        "property": "Harbour View Terrace, Sydney",
        "coverage": "$1,200,000",
        "new_coverage": "$1,500,000"
    },
    "56789": {
        "name": "James",
        "property": "Mountain View Crescent, Brighton",
        "coverage": "$950,000",
        "new_coverage": "$1,200,000"
    }
}


def get_customer_by_code(code: str) -> dict:
    """Get customer info by verification code."""
    # Normalize code (remove spaces)
    normalized = code.replace(" ", "").strip()
    return CUSTOMER_DATABASE.get(normalized)


def create_system_prompt_for_customer(customer: dict) -> str:
    """Create dynamic system prompt based on customer context."""
    if not customer:
        return "You are an insurance broker assistant."
    
    return f"""You are an AI assistant for an insurance brokerage company.

CUSTOMER CONTEXT:
- Name: {customer['name']}
- Property: {customer['property']}
- Current Coverage: {customer['coverage']}

CONVERSATION FLOW:
1. When customer greets and inquires about policy, respond:
   "Thank you for calling our brokerage. I can see you're calling from your mobile. 
    I've just sent you an SMS text with a verification code. Please read the numbers to me."

2. When they provide verification code, respond:
   "That is correct. How can I help you today {customer['name']}?"

3. When they request coverage increase, respond:
   "No problem, pulling your file now. Please confirm you are referring to the {customer['property']} property?"

4. When they confirm property, respond:
   "OK, we've just prepared a PDS for you. Once you confirm the adjustments, we can lock it in for you."

5. When they confirm PDS, respond:
   "Thank you for your business. We have updated the policy from {customer['coverage']} to {customer['new_coverage']}, 
    and the updated policy schedule has been sent to you. Is there anything else you need help with?"

6. When they say no/thank you, respond:
   "Thank you for calling. Have a great day\!"

Be professional and follow this exact flow."""


class MultiCustomerFlowTester:
    """Test conversational flows with multiple customers and real-time AI audio."""
    
    def __init__(self):
        """Initialize tester."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=api_key)
        self.audio_player = AudioPlayer()
        self.audio_dir = Path(__file__).parent / "audio_fixtures"
        
        # Current conversation state
        self.current_customer = None
        self.history = []
        self.conversation_log = []
    
    def load_customer_audio(self, customer_code: str, filename: str) -> np.ndarray:
        """Load pre-recorded customer audio file."""
        audio_path = self.audio_dir / f"customer_{customer_code}" / filename
        
        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio fixture not found: {audio_path}\n"
                f"Run: python3 -m tests.custom.generate_audio_fixtures"
            )
        
        with wave.open(str(audio_path), 'rb') as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            return audio_float
    
    def transcribe_customer_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe customer audio using Whisper."""
        audio_wav = numpy_to_wav_bytes(audio_data, sample_rate=16000)
        
        transcription = self.client.audio.transcriptions.create(
            model='whisper-1',
            file=('audio.wav', audio_wav, 'audio/wav')
        )
        
        return transcription.text.strip()
    
    def generate_ai_response_with_audio(self, user_text: str) -> tuple:
        """
        Generate AI response with REAL-TIME audio generation.
        
        Returns:
            (ai_text, ai_audio_bytes)
        """
        # Add user message to history
        self.history.append({
            'role': 'user',
            'content': user_text
        })
        
        # Build messages with system prompt
        system_prompt = create_system_prompt_for_customer(self.current_customer)
        messages = [{'role': 'system', 'content': system_prompt}] + self.history
        
        # Get AI response with audio
        response = self.client.chat.completions.create(
            model='gpt-4o-audio-preview',
            modalities=['text', 'audio'],
            audio={'voice': 'alloy', 'format': 'wav'},
            messages=messages
        )
        
        # Extract text
        message = response.choices[0].message
        ai_text = message.content
        
        if ai_text is None and hasattr(message, 'audio') and message.audio:
            if hasattr(message.audio, 'transcript'):
                ai_text = message.audio.transcript
            else:
                ai_text = "[Audio response]"
        
        # Extract audio
        ai_audio = None
        if hasattr(message, 'audio') and message.audio:
            audio_data = message.audio.data
            ai_audio = base64.b64decode(audio_data)
        
        # Add to history
        self.history.append({
            'role': 'assistant',
            'content': ai_text
        })
        
        return ai_text, ai_audio
    
    def simulate_turn(self, customer_code: str, audio_file: str, expected_keywords: list) -> bool:
        """
        Simulate one conversation turn.
        
        Args:
            customer_code: Customer verification code
            audio_file: Pre-recorded customer audio filename
            expected_keywords: Keywords to validate in AI response
        """
        print(f"\n{'='*70}")
        print(f"CUSTOMER: {audio_file}")
        
        try:
            # 1. Load pre-recorded CUSTOMER audio
            customer_audio = self.load_customer_audio(customer_code, audio_file)
            
            # 2. Transcribe customer speech
            customer_text = self.transcribe_customer_audio(customer_audio)
            print(f"CUSTOMER (transcribed): {customer_text}")
            
            # 3. Check if this is verification code turn
            if "02_verification" in audio_file:
                # Extract verification code and set customer context
                code = customer_text.replace(" ", "").strip()
                self.current_customer = get_customer_by_code(code)
                if self.current_customer:
                    print(f"✓ Customer identified: {self.current_customer['name']}")
                else:
                    print(f"⚠ Unknown verification code: {code}")
            
            # 4. Generate AI response with REAL-TIME audio
            print("AI: Generating response...")
            ai_text, ai_audio = self.generate_ai_response_with_audio(customer_text)
            print(f"AI: {ai_text}")
            
            # 5. Play AI audio (real-time generated, not pre-recorded\!)
            if ai_audio:
                print("AI: Playing audio response...")
                self.audio_player.play_wav(ai_audio)
                time.sleep(1)  # Brief pause for natural flow
            
            # 6. Log conversation
            self.conversation_log.append({
                'audio_file': audio_file,
                'customer_text': customer_text,
                'ai_text': ai_text
            })
            
            # 7. Validate keywords
            ai_lower = ai_text.lower()
            found = [kw for kw in expected_keywords if kw.lower() in ai_lower]
            missing = [kw for kw in expected_keywords if kw.lower() not in ai_lower]
            
            if missing:
                print(f"⚠ Missing keywords: {missing}")
                return False
            else:
                print(f"✓ Validated: {found}")
                return True
                
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_customer_conversation(self, customer_code: str) -> bool:
        """Test complete conversation flow for one customer."""
        customer = CUSTOMER_DATABASE[customer_code]
        
        print("\n" + "="*70)
        print(f"TESTING CUSTOMER: {customer['name']} (Code: {customer_code})")
        print(f"Property: {customer['property']}")
        print("="*70)
        
        # Reset state for this customer
        self.current_customer = None
        self.history = []
        
        # Conversation flow
        turns = [
            ("01_greeting.wav", ["mobile", "SMS", "verification"]),
            ("02_verification.wav", ["correct", customer['name']]),
            ("03_request.wav", ["pulling", "file", customer['property'].split(',')[0]]),
            ("04_confirm.wav", ["PDS", "confirm", "lock"]),
            ("05_proceed.wav", ["updated", "policy", customer['new_coverage']]),
            ("06_thanks.wav", ["thank", "great day"])
        ]
        
        success = True
        for audio_file, keywords in turns:
            success &= self.simulate_turn(customer_code, audio_file, keywords)
        
        return success
    
    def print_summary(self):
        """Print conversation summary."""
        print("\n" + "="*70)
        print("CONVERSATION SUMMARY")
        print("="*70)
        
        for i, turn in enumerate(self.conversation_log, 1):
            print(f"\nTurn {i}:")
            print(f"  Customer: {turn['customer_text']}")
            print(f"  AI: {turn['ai_text']}")


def main():
    """Run multi-customer conversational flow tests."""
    print("="*70)
    print("MULTI-CUSTOMER CONVERSATIONAL FLOW TEST")
    print("="*70)
    print("\nThis test simulates 5 different customers calling about their policies.")
    print("- Customer audio: Pre-recorded (simulating real callers)")
    print("- AI audio: Generated in REAL-TIME via OpenAI TTS API")
    print("- Context: Switches dynamically based on verification codes")
    
    try:
        tester = MultiCustomerFlowTester()
        
        # Test each customer
        results = {}
        for code, customer in CUSTOMER_DATABASE.items():
            try:
                success = tester.test_customer_conversation(code)
                results[customer['name']] = success
                
                # Brief pause between customers
                time.sleep(2)
                
            except Exception as e:
                print(f"\n✗ Error testing {customer['name']}: {e}")
                results[customer['name']] = False
        
        # Print final results
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        
        for name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {name}")
        
        all_passed = all(results.values())
        total = len(results)
        passed = sum(results.values())
        
        print(f"\nTotal: {passed}/{total} customers passed")
        
        if all_passed:
            print("\n🎉 ALL CUSTOMERS TESTED SUCCESSFULLY\!")
            print("   - Pre-recorded customer audio processed")
            print("   - Real-time AI audio generated and played")
            print("   - Context switching validated")
            return True
        else:
            print("\n⚠ SOME TESTS FAILED - Review logs above")
            return False
            
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("\nPlease generate audio fixtures first:")
        print("  python3 -m tests.custom.generate_audio_fixtures")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
