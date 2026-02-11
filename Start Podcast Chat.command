#!/bin/bash
# Double-click this file to start Podcast Chat!
cd "$(dirname "$0")"

# Run setup first (installs dependencies if needed)
./setup.sh

# If setup succeeded, start the app
if [ $? -eq 0 ]; then
    ./start.sh
else
    echo ""
    echo "Setup failed. Please check the errors above."
    read -p "Press Enter to close..."
fi
