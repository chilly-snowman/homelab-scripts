#!/usr/bin/env bash
WATCH_DIR="/srv/media/raw"
LOG_FILE="/var/log/post_ingest.log"
JELLYFIN_URL="http://localhost:8096"
JELLYFIN_API_KEY="3ab326bae64942cea4abdf9ac3fa319b"

inotifywait -m -r -e close_write,moved_to --format '%w%f' "$WATCH_DIR" | while read -r FILE
do
    case "$FILE" in
        *.mkv)
            echo "$(date '+%F %T') detected: $FILE" | sudo tee -a "$LOG_FILE" >/dev/null
            sudo chown zane:zane "$FILE"
            sudo chmod 664 "$FILE"
            echo "$(date '+%F %T') fixed ownership: $FILE" | sudo tee -a "$LOG_FILE" >/dev/null
            curl -s -X POST "$JELLYFIN_URL/Library/Refresh" \
                -H "X-Emby-Token: $JELLYFIN_API_KEY" >/dev/null
            echo "$(date '+%F %T') triggered jellyfin scan" | sudo tee -a "$LOG_FILE" >/dev/null
            ;;
    esac
done

