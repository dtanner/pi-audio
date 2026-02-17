#!/usr/bin/env bash
#
# Capture screenshots and screen recordings from the Pi remotely
#
# Usage:
#   ./capture.sh screenshot              # Take screenshot, copy to local
#   ./capture.sh record start            # Start screen recording
#   ./capture.sh record stop             # Stop recording, copy to local
#
# Prerequisites (installed automatically on first use):
#   Pi: grim (screenshots), wf-recorder (recordings)
#
# Configuration (same as deploy.sh):
#   PI_HOST  - SSH target (default: admin@piaudio.local)

set -e

PI_HOST="${PI_HOST:-admin@piaudio.local}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)/captures"
PID_FILE="/tmp/pi-audio-recording.pid"
REMOTE_FILE_REF="/tmp/pi-audio-recording-file"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

ensure_deps() {
    local tool="$1"
    ssh "$PI_HOST" "command -v $tool > /dev/null 2>&1 || (echo 'Installing $tool...' && sudo apt install -y $tool)"
}

mkdir -p "$LOCAL_DIR"

case "${1:-}" in
    screenshot)
        ensure_deps grim
        TIMESTAMP=$(date +%Y%m%d-%H%M%S)
        REMOTE_PATH="/tmp/pi-audio-screenshot-${TIMESTAMP}.png"
        echo -e "${BLUE}Taking screenshot...${NC}"
        ssh "$PI_HOST" "grim $REMOTE_PATH"
        scp "$PI_HOST:$REMOTE_PATH" "$LOCAL_DIR/screenshot-${TIMESTAMP}.png"
        ssh "$PI_HOST" "rm $REMOTE_PATH"
        echo -e "${GREEN}Saved to captures/screenshot-${TIMESTAMP}.png${NC}"
        ;;

    record)
        case "${2:-}" in
            start)
                ensure_deps wf-recorder
                TIMESTAMP=$(date +%Y%m%d-%H%M%S)
                REMOTE_PATH="/tmp/pi-audio-recording-${TIMESTAMP}.mp4"
                echo -e "${BLUE}Starting recording...${NC}"
                ssh "$PI_HOST" "nohup wf-recorder -f $REMOTE_PATH > /dev/null 2>&1 & echo \$!"  > "$PID_FILE"
                echo "$REMOTE_PATH" > "$REMOTE_FILE_REF"
                echo -e "${GREEN}Recording started (PID: $(cat "$PID_FILE"))${NC}"
                echo -e "Run ${BLUE}./capture.sh record stop${NC} to finish."
                ;;
            stop)
                if [[ ! -f "$PID_FILE" ]]; then
                    echo -e "${RED}No recording in progress.${NC}"
                    exit 1
                fi
                PID=$(cat "$PID_FILE")
                REMOTE_PATH=$(cat "$REMOTE_FILE_REF")
                FILENAME=$(basename "$REMOTE_PATH")
                echo -e "${BLUE}Stopping recording (PID: $PID)...${NC}"
                ssh "$PI_HOST" "kill -INT $PID 2>/dev/null || true"
                sleep 1
                scp "$PI_HOST:$REMOTE_PATH" "$LOCAL_DIR/$FILENAME"
                ssh "$PI_HOST" "rm -f $REMOTE_PATH"
                rm -f "$PID_FILE" "$REMOTE_FILE_REF"
                echo -e "${GREEN}Saved to captures/${FILENAME}${NC}"
                ;;
            *)
                echo "Usage: $0 record start|stop"
                exit 1
                ;;
        esac
        ;;

    *)
        echo "Usage:"
        echo "  $0 screenshot          Take a screenshot"
        echo "  $0 record start        Start screen recording"
        echo "  $0 record stop         Stop recording"
        exit 1
        ;;
esac
