#!/usr/bin/env bash

BIN_PATH="${BIN_PATH:-devops/db_backup/}"

UPLOAD_FILE="${1}"
UPLOAD_TARGET_URL="gs://${STORAGE_BUCKET_NAME}/`date +${BACKUP_FILE_TEMPLATE:-%y-%m-%d-%H-%M}`.sql"

if [ ! -f "${UPLOAD_FILE}" ]; then
    echo " > dbdump file was not found";
    exit 1
fi

echo " > uploading from ${UPLOAD_FILE} to ${UPLOAD_TARGET_URL}"
$BIN_PATH/google_auth.sh || exit 2
if ! gsutil cp "${UPLOAD_FILE}" "${UPLOAD_TARGET_URL}"; then
    echo " > Upload failed"
    exit 3
fi

echo " > Uploaded db backup to ${UPLOAD_TARGET_URL}"
exit 0
