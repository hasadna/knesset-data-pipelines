#!/usr/bin/env bash

export BIN_PATH="${BIN_PATH:-devops/db_backup/}"
export BACKUP_INITIAL_DELAY_SECONDS="${BACKUP_INITIAL_DELAY_SECONDS:-15}"
export RESTORE_GS_URL="${RESTORE_GS_URL}"

echo " > sleeping ${BACKUP_INITIAL_DELAY_SECONDS} seconds to allow DB to start properly";
sleep "${BACKUP_INITIAL_DELAY_SECONDS}";

if [ "${RESTORE_GS_URL}" != "" ]; then
    $BIN_PATH/google_storage_restore.sh "${RESTORE_GS_URL}" /restore.sql
else
    $BIN_PATH/backup_daemon.sh /dump.sql
fi
