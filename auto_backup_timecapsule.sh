#!/bin/bash

# Create local, ignored backups. Private capsule data must never be committed.
FILE_PATH="data/time_capsules.json"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
LOGS_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOGS_DIR/backup_script_log.txt"
BACKUP_DIR="$REPO_ROOT/backups"

log_message() {
    mkdir -p "$LOGS_DIR"
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

cd "$REPO_ROOT" || { log_message "Error: Could not navigate to repo root"; exit 1; }

log_message "Starting local backup for $FILE_PATH"

if [ ! -f "$FILE_PATH" ]; then
    log_message "Error: $FILE_PATH does not exist."
    exit 1
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/time_capsules_$(date +'%Y%m%d_%H%M%S').json"
cp "$FILE_PATH" "$BACKUP_FILE" || { log_message "Error: Backup failed"; exit 1; }
chmod 600 "$BACKUP_FILE"
log_message "Saved private backup to $BACKUP_FILE"

log_message "Local backup finished."
echo "----------------------------------------" >> "$LOG_FILE"
exit 0
