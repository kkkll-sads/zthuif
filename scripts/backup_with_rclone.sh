#!/usr/bin/env bash
set -euo pipefail

# ===============================================
# SQLite databases → rclone remote backup (e.g., Google Drive)
# Prerequisites:
#   1) Install rclone: https://rclone.org/install/
#   2) Configure a remote: rclone config (e.g., name it 'gdrive')
# Usage (once):
#   chmod +x scripts/backup_with_rclone.sh
#   ./scripts/backup_with_rclone.sh --remote gdrive:Backups/pypo
# Cron:
#   0 3 * * * /root/zthuif-main/scripts/backup_with_rclone.sh --remote gdrive:Backups/pypo >> /var/log/pypo-backup.log 2>&1
# ===============================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="${PROJECT_DIR}/instance"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="pypo_sqlite_${TIMESTAMP}.tar.gz"
REMOTE=""
KEEP="15"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="$2"; shift 2;;
    --keep)
      KEEP="$2"; shift 2;;
    *)
      echo "Unknown arg: $1"; exit 2;;
  esac
done

if [[ -z "${REMOTE}" ]]; then
  echo "Usage: $0 --remote <rclone-remote:path> [--keep N]"
  exit 2
fi

mkdir -p "${BACKUP_DIR}"

# 1) 打包 SQLite 数据库
cd "${PROJECT_DIR}"
if [[ ! -d "${DB_DIR}" ]]; then
  echo "No instance dir: ${DB_DIR}"; exit 1
fi

tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "${DB_DIR}" .

echo "Created archive: ${BACKUP_DIR}/${ARCHIVE_NAME}"

# 2) 上传至 rclone 远端
if ! command -v rclone >/dev/null 2>&1; then
  echo "[ERR] rclone is not installed. See https://rclone.org/install/"
  exit 1
fi

rclone copy "${BACKUP_DIR}/${ARCHIVE_NAME}" "${REMOTE}/" --log-level NOTICE

# 3) 在远端保留最近 N 份（按文件名排序）
# 依赖 rclone 的排序与删除命令
if [[ -n "${KEEP}" ]]; then
  # 列出远端归档，按文件名逆序(新→旧)，跳过前 KEEP 个，其余删除
  mapfile -t OLD_FILES < <(rclone lsf --files-only --format "p" "${REMOTE}" | grep '^pypo_sqlite_.*\.tar\.gz$' | sort -r | tail -n +$((KEEP+1)))
  for f in "${OLD_FILES[@]:-}"; do
    [[ -n "$f" ]] && rclone deletefile "${REMOTE}/$f"
  done
fi

echo "[OK] backup uploaded to ${REMOTE} and rotation applied (keep=${KEEP})"
