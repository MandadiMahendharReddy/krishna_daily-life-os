#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ENV="${ROOT_DIR}/.backup.env"
BACKUP_DIR="${ROOT_DIR}/backups"

if [[ ! -f "${BACKUP_ENV}" ]]; then
    echo "Missing ${BACKUP_ENV}."
    exit 1
fi

set -a
source "${BACKUP_ENV}"
set +a

if [[ -z "${RENDER_BACKUP_DATABASE_URL:-}" ]]; then
    echo "RENDER_BACKUP_DATABASE_URL is not configured."
    exit 1
fi

mkdir -p "${BACKUP_DIR}"
timestamp="$(date +%Y-%m-%d_%H-%M-%S)"
backup_file="${BACKUP_DIR}/krishna_daily_life_os_${timestamp}.json.gz"
partial_file="${BACKUP_DIR}/.krishna_daily_life_os_${timestamp}.json.partial"
trap 'rm -f "${partial_file}" "${partial_file}.gz"' EXIT

DATABASE_URL="${RENDER_BACKUP_DATABASE_URL}" \
    "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/manage.py" dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude contenttypes \
    --exclude auth.permission \
    --indent 2 \
    --output "${partial_file}"

gzip -9 "${partial_file}"
mv "${partial_file}.gz" "${backup_file}"
ln -sfn "$(basename "${backup_file}")" "${BACKUP_DIR}/latest.json.gz"
trap - EXIT
echo "Backup created: ${backup_file}"
