#!/bin/sh
set -eu

repository_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "This script must run inside the repository." >&2
    exit 1
}
capsule_file="$repository_root/data/time_capsules.json"
backup_directory="${BACKUP_DIR:-$repository_root/data/manual-backups}"
retention="${BACKUP_RETENTION:-30}"

if [ ! -f "$capsule_file" ]; then
    echo "Private capsule store does not exist: $capsule_file" >&2
    exit 1
fi

mkdir -p "$backup_directory"
chmod 700 "$backup_directory"
timestamp=$(date -u +'%Y%m%dT%H%M%SZ')
temporary_backup="$backup_directory/.time_capsules_${timestamp}.tmp"
final_backup="$backup_directory/time_capsules_${timestamp}.json"

cp "$capsule_file" "$temporary_backup"
chmod 600 "$temporary_backup"
mv "$temporary_backup" "$final_backup"

find "$backup_directory" -type f -name 'time_capsules_*.json' -print \
    | sort -r \
    | awk -v keep="$retention" 'NR > keep' \
    | while IFS= read -r old_backup; do
        rm -f -- "$old_backup"
      done

echo "Private backup saved: $final_backup"
