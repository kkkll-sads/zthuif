#!/usr/bin/env bash
set -euo pipefail

# ===============================================
# SQLite databases → Google Cloud Storage backup
# Usage (once):
#   sudo chmod +x scripts/backup_to_gcs.sh
#   sudo ./scripts/backup_to_gcs.sh --bucket gs://your-bucket --sa /path/to/service-account.json
# Cron (edit with `crontab -e` for root):
#   0 3 * * * /root/zthuif-main/scripts/backup_to_gcs.sh --bucket gs://your-bucket --sa /root/sa.json >> /var/log/pypo-backup.log 2>&1
# ===============================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="${PROJECT_DIR}/instance"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="pypo_sqlite_${TIMESTAMP}.tar.gz"

BUCKET=""
SA_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)
      BUCKET="$2"; shift 2;;
    --sa)
      SA_KEY="$2"; shift 2;;
    *)
      echo "Unknown arg: $1"; exit 2;;
  esac
done

if [[ -z "${BUCKET}" || -z "${SA_KEY}" ]]; then
  echo "Usage: $0 --bucket gs://your-bucket --sa /path/to/service-account.json"
  exit 2
fi

mkdir -p "${BACKUP_DIR}"

# 1) Freeze SQLite files (best effort) and archive
cd "${PROJECT_DIR}"
if [[ ! -d "${DB_DIR}" ]]; then
  echo "No instance dir: ${DB_DIR}"; exit 1
fi

tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "${DB_DIR}" .

echo "Created archive: ${BACKUP_DIR}/${ARCHIVE_NAME}"

# 2) Upload to GCS using gcloud-less approach (python lib)
#    Requires google-cloud-storage in venv
if [[ -x "${PROJECT_DIR}/venv/bin/python" ]]; then
  GCS_BUCKET="${BUCKET}" GCS_SA="${SA_KEY}" ARCHIVE_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}" \
  "${PROJECT_DIR}/venv/bin/python" - <<PY
import os, sys
from google.cloud import storage

sa_path = os.environ.get('GCS_SA')
if not sa_path or not os.path.exists(sa_path):
    print('[ERR] service account json not found:', sa_path)
    sys.exit(1)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = sa_path

bucket_uri = os.environ['GCS_BUCKET']
if not bucket_uri.startswith('gs://'):
    print('[ERR] bucket must start with gs://')
    sys.exit(2)

bucket_name = bucket_uri.replace('gs://','').split('/')[0]
prefix = '/'.join(bucket_uri.replace('gs://','').split('/')[1:])

client = storage.Client()
bucket = client.bucket(bucket_name)

archive_path = os.environ['ARCHIVE_PATH']
key = f"{prefix}/{os.path.basename(archive_path)}" if prefix else os.path.basename(archive_path)
blob = bucket.blob(key)
blob.upload_from_filename(archive_path)
print('[OK] uploaded to', f'gs://{bucket_name}/{key}')
PY
else
  echo "[ERR] Python venv not found at ${PROJECT_DIR}/venv."
  exit 1
fi
