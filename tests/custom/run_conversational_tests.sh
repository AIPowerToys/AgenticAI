#!/bin/bash
# Quick start script for conversational flow tests

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║       Conversational Flow Testing - Quick Start                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo

# Check if audio fixtures exist
AUDIO_DIR="tests/custom/audio_fixtures"

if [ ! -d "$AUDIO_DIR" ] || [ -z "$(ls -A $AUDIO_DIR 2>/dev/null)" ]; then
    echo "📁 Audio fixtures not found. Generating them now..."
    echo
    python3 -m tests.custom.generate_audio_fixtures
    echo
else
    echo "✓ Audio fixtures found in $AUDIO_DIR"
    echo "  Files: $(ls $AUDIO_DIR/*.wav 2>/dev/null | wc -l | tr -d ' ')"
    echo
fi

# Run the conversational flow test
echo "🧪 Running conversational flow test..."
echo "═══════════════════════════════════════════════════════════════════════"
echo

python3 -m tests.custom.test_update_policy_conversational_flow

echo
echo "═══════════════════════════════════════════════════════════════════════"
echo "✅ Conversational flow test complete!"
echo
