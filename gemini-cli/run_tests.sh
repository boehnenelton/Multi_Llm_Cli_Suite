#!/bin/bash
# Gemini Multi-Model Test Suite
# Automates prompter.py execution across all models in registry.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROMPT="Hello. This is a standardization test. Please identify your model name and version, and briefly describe your primary function in one sentence."

echo "=== STARTING GEMINI MULTI-MODEL TEST ==="

# 1. Gemini 3.1 Pro
echo "[1/5] Testing Gemini 3.1 Pro..."
python3 $DIR/prompter.py "$PROMPT" --model "gemini-3.1-pro-preview" --output "$DIR/output/gemini-3.1-pro.txt"

# 2. Gemini 3 Flash
echo "[2/5] Testing Gemini 3 Flash..."
python3 $DIR/prompter.py "$PROMPT" --model "gemini-3-flash-preview" --output "$DIR/output/gemini-3-flash.txt"

# 3. Gemini 3.1 Flash-Lite
echo "[3/5] Testing Gemini 3.1 Flash-Lite..."
python3 $DIR/prompter.py "$PROMPT" --model "gemini-3.1-flash-lite-preview" --output "$DIR/output/gemini-3.1-flash-lite.txt"

# 4. Gemini Flash-Lite Latest
echo "[4/5] Testing Gemini Flash-Lite Latest..."
python3 $DIR/prompter.py "$PROMPT" --model "gemini-flash-lite-latest" --output "$DIR/output/gemini-flash-lite-latest.txt"

# 5. Gemini 2.5 Flash
echo "[5/5] Testing Gemini 2.5 Flash..."
python3 $DIR/prompter.py "$PROMPT" --model "gemini-2.5-flash" --output "$DIR/output/gemini-2.5-flash.txt"

echo "=== TESTS COMPLETE. CHECK output/ FOLDER ==="
