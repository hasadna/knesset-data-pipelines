#!/usr/bin/env bash

export RESTORE_GS_URL="${1}"  # google storage url to download the dump from
export RESTORE_FILE="${2}"  # this file will contain the downloaded sql dump
export BIN_PATH="${BIN_PATH:-devops/db_backup/}"

echo " > Running DB restore job"
echo " > RESTORE_GS_URL=${RESTORE_GS_URL} RESTORE_FILE=${RESTORE_FILE}"

if ! $BIN_PATH/google_auth.sh; then
    echo " > failed google auth"
    exit 1
fi

echo " > downloading from ${RESTORE_GS_URL}"
if ! gsutil cp "${RESTORE_GS_URL}" "${RESTORE_FILE}"; then
    echo " > failed to download from google storage"
    exit 2
fi

echo " > restoring from ${RESTORE_FILE}"
if ! psql -f "${RESTORE_FILE}"; then
    echo " > failed to load the dump to the sql server"
    exit 3
fi

echo " > restored successfully"
exit 0
