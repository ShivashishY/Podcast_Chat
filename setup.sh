#!/bin/bash

# Podcast Chat - One-Click Setup Script
# This script sets up everything needed to run the Podcast Chat app

echo "🎙️  Podcast Chat - Setup"
echo "========================"
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

# Step 1: Check for Homebrew (needed for ffmpeg)
echo "📦 Checking dependencies..."
if ! command_exists brew; then
    echo -e "${YELLOW}Installing Homebrew (package manager for macOS)...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Step 2: Install FFmpeg (needed for audio processing)
if ! command_exists ffmpeg; then
    echo -e "${YELLOW}Installing FFmpeg (for audio processing)...${NC}"
    brew install ffmpeg
else
    echo -e "${GREEN}✓ FFmpeg is installed${NC}"
fi

# Step 3: Check/Install Python
if ! command_exists python3; then
    echo -e "${YELLOW}Installing Python...${NC}"
    brew install python
else
    echo -e "${GREEN}✓ Python is installed${NC}"
fi

# Step 4: Install Ollama
if ! command_exists ollama; then
    echo -e "${YELLOW}Installing Ollama (local AI)...${NC}"
    brew install ollama
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi

# Step 5: Create Python virtual environment
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

# Step 6: Download Ollama model
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

# Step 7: Create .env file if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "SMALLEST_API_KEY=your_api_key_here" > "$SCRIPT_DIR/.env"
    echo "SECRET_KEY=$SECRET" >> "$SCRIPT_DIR/.env"
    echo -e "${YELLOW}Note: Add your Smallest AI API key to .env file for transcription${NC}"
else
    # Add SECRET_KEY if not present
    if ! grep -q "SECRET_KEY" "$SCRIPT_DIR/.env"; then
        SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "SECRET_KEY=$SECRET" >> "$SCRIPT_DIR/.env"
        echo -e "${GREEN}✓ Added SECRET_KEY to .env${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "To start the app, double-click 'Start Podcast Chat.command'"
echo "Or run: ./start.sh"
echo ""
