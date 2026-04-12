#!/bin/bash
# Start Voice Dictate
# Usage: ./start.sh [--hotkey cmd_r] [--model mlx-community/gemma-4-e4b-it-4bit]

DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/voice_dictate.py" "$@"
