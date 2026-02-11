#!/bin/bash

# Podcast Chat - One-Click Launcher
# Double-click this file to start the app!

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo "🎙️  Starting Podcast Chat..."
echo "==========================="
echo ""

# Check if setup has been run
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${YELLOW}First time setup required. Running setup...${NC}"
    echo ""
    bash "$SCRIPT_DIR/setup.sh"
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Starting AI engine..."
    ollama serve &>/dev/null &
    sleep 2
fi

# Check if Ollama model exists
if ! ollama list 2>/dev/null | grep -q "llama3.2"; then
    echo "Downloading AI model (first time only)..."
    ollama pull llama3.2
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Kill any existing instance on port 5000
lsof -ti:5000 | xargs kill -9 2>/dev/null

echo ""
echo -e "${GREEN}✓ AI engine ready${NC}"
echo -e "${GREEN}✓ Starting web server...${NC}"
echo ""
echo "=========================================="
echo "🌐 Open your browser to:"
echo ""
echo "   http://localhost:5000"
echo ""
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the app"
echo ""

# Open browser automatically after a short delay
(sleep 2 && open "http://localhost:5000") &

# Start the Flask app
python "$SCRIPT_DIR/app.py"
