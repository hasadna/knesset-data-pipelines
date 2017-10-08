#!/usr/bin/env bash

trap "exit 1" SIGTERM;
trap "exit 2" SIGINT;

export DUMP_FILE="${1}"  # sql file which will be used for local storage of the dump before uploading
export BIN_PATH="${BIN_PATH:-devops/db_backup/}"
export BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"

if [ "${BACKUP_INTERVAL_SECONDS}" == "0" ]; then
    echo " > Running a backup"
else
    echo " > Running DB backup daemon"
fi
echo " > DUMP_FILE=${DUMP_FILE} BACKUP_INTERVAL_SECONDS=${BACKUP_INTERVAL_SECONDS}"
while true; do
    if ! $BIN_PATH/db_dump_retry.sh "${DUMP_FILE}"; then
        echo " > db dump failure"
        exit 3
    fi
    if ! $BIN_PATH/google_storage_upload.sh "${DUMP_FILE}"; then
        echo " > google storage upload failure"
        exit 4
    fi
    if [ "${BACKUP_INTERVAL_SECONDS}" == "0" ]; then
        exit 0
    else
        echo " > sleeping ${BACKUP_INTERVAL_SECONDS} seconds until next backup";
        sleep "${BACKUP_INTERVAL_SECONDS}";
    fi
done

exit 5
