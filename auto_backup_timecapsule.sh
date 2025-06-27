#!/bin/bash

# 配置
FILE_PATH="data/time_capsules.json"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
LOGS_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOGS_DIR/backup_script_log.txt"

log_message() {
    mkdir -p "$LOGS_DIR"
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

cd "$REPO_ROOT" || { log_message "Error: Could not navigate to repo root"; exit 1; }

log_message "Starting backup for $FILE_PATH"

if [ ! -f "$FILE_PATH" ]; then
    log_message "Error: $FILE_PATH does not exist."
    exit 1
fi

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "main" ]; then
    log_message "Not on main branch, switching..."
    git checkout main || { log_message "Error: Could not switch to main"; exit 1; }
fi

git add "$FILE_PATH"
if git diff --cached --quiet; then
    log_message "No changes to commit."
else
    commit_msg="Auto backup: $FILE_PATH $(date +'%Y-%m-%d %H:%M:%S')"
    git commit -m "$commit_msg"
    log_message "Committed: $commit_msg"
fi

if [ "$1" == "push" ]; then
    if git push origin main; then
        log_message "Pushed to origin/main."
    else
        log_message "Error: Push failed."
    fi
fi

log_message "Backup script finished."
echo "----------------------------------------" >> "$LOG_FILE"
exit 0