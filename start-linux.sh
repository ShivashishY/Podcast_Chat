#!/bin/bash

# Podcast Chat - Linux One-Click Launcher
# Run: chmod +x start-linux.sh && ./start-linux.sh

echo ""
echo "🎙️  Podcast Chat - Linux Setup"
echo "==============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check for Python
echo "📦 Checking dependencies..."
if ! command_exists python3; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo ""
    echo "Please install Python 3.10+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    echo "  Arch: sudo pacman -S python python-pip"
    exit 1
else
    echo -e "${GREEN}✓ Python is installed${NC}"
fi

# Step 2: Check for FFmpeg
if ! command_exists ffmpeg; then
    echo -e "${YELLOW}⚠ FFmpeg is not installed${NC}"
    echo ""
    echo "Installing FFmpeg is recommended for audio processing:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo "  Arch: sudo pacman -S ffmpeg"
    echo ""
    read -p "Continue without FFmpeg? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ FFmpeg is installed${NC}"
fi

# Step 3: Check for Ollama
if ! command_exists ollama; then
    echo -e "${YELLOW}⚠ Ollama is not installed (needed for AI chat)${NC}"
    echo ""
    echo "Install Ollama for AI features:"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    echo ""
    echo "Continuing without AI chat features..."
    OLLAMA_AVAILABLE=false
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
    OLLAMA_AVAILABLE=true
fi

# Step 4: Create Python virtual environment
echo ""
echo "🐍 Setting up Python environment..."
VENV_PATH="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi

# Activate venv and install dependencies
source "$VENV_PATH/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

echo -e "${GREEN}✓ Python packages installed${NC}"

# Step 5: Setup Ollama if available
if [ "$OLLAMA_AVAILABLE" = true ]; then
    echo ""
    echo "🤖 Setting up AI model..."
    
    # Start Ollama service if not running
    if ! pgrep -x "ollama" > /dev/null; then
        ollama serve &>/dev/null &
        sleep 3
    fi
    
    # Check if model exists, download if not
    if ! ollama list 2>/dev/null | grep -q "llama3.2"; then
        echo "Downloading AI model (this may take a few minutes on first run)..."
        ollama pull llama3.2
    fi
    
    echo -e "${GREEN}✓ AI model ready${NC}"
fi

# Step 6: Create .env file if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo -e "${YELLOW}Note: Edit .env and add your Smallest AI API key${NC}"
fi

# Step 7: Kill any existing instance on port 5000
if command_exists lsof; then
    lsof -ti:5000 | xargs kill -9 2>/dev/null
elif command_exists fuser; then
    fuser -k 5000/tcp 2>/dev/null
fi

# Start the app
echo ""
echo "=========================================="
echo "🌐 Starting Podcast Chat..."
echo ""
echo "   Open your browser to:"
echo "   http://localhost:5000"
echo ""
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the app"
echo ""

python app.py
