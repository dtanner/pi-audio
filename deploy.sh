#!/usr/bin/env bash
#
# Deploy pi-audio to Raspberry Pi
#
# Usage:
#   ./deploy.sh           # Sync files only
#   ./deploy.sh --run     # Sync files and run the app on Pi

set -e

# Configuration (can be overridden via environment variables)
PI_HOST="${PI_HOST:-admin@piaudio.local}"
PI_PATH="${PI_PATH:-~/pi-audio}"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
RUN_APP=false
if [[ "$1" == "--run" ]]; then
    RUN_APP=true
fi

echo -e "${BLUE}Syncing files to Pi...${NC}"
rsync -avz \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.ruff_cache' \
    --exclude='.idea' \
    "$LOCAL_PATH/" "$PI_HOST:$PI_PATH/"

echo -e "${GREEN}✓ Files synced to $PI_HOST:$PI_PATH${NC}"

# Install application and add to taskbar
echo -e "${BLUE}Installing application...${NC}"
ssh "$PI_HOST" "mkdir -p ~/.local/share/applications && cp $PI_PATH/pi-audio.desktop ~/.local/share/applications/"
# Add pi-audio to the taskbar launchers if not already present
ssh "$PI_HOST" "if ! grep -q 'pi-audio' ~/.config/wf-panel-pi/wf-panel-pi.ini 2>/dev/null; then
    cp /etc/xdg/wf-panel-pi/wf-panel-pi.ini ~/.config/wf-panel-pi/wf-panel-pi.ini 2>/dev/null
    sed -i 's/^launchers=.*/& pi-audio/' ~/.config/wf-panel-pi/wf-panel-pi.ini
    echo 'Restart the panel or log out/in to see the taskbar launcher.'
fi"
echo -e "${GREEN}✓ Application installed (available in taskbar and app menu)${NC}"

if [[ "$RUN_APP" == true ]]; then
    echo -e "${BLUE}Running app on Pi...${NC}"
    echo -e "${BLUE}(Press Ctrl+C to stop, or use the EXIT button on the display)${NC}"
    ssh "$PI_HOST" "cd $PI_PATH && source .venv/bin/activate && python -m pi_audio"
else
    echo ""
    echo "To run the app on the Pi:"
    echo "  ssh $PI_HOST"
    echo "  cd $PI_PATH"
    echo "  source .venv/bin/activate"
    echo "  python -m pi_audio"
    echo ""
    echo "Or use: ./deploy.sh --run"
fi
