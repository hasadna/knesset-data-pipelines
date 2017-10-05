#!/usr/bin/env bash

BIN_PATH="${BIN_PATH:-devops/db_backup/}"

DB_DUMP_FILE="${1}"
MAX_RETRIES="${BACKUP_MAX_RETRIES:-5}"
SECONDS_BETWEEN_RETRIES="${BACKUP_SECONDS_BETWEEN_RETRIES:-5}"

echo " > Creating DB dump ${DB_DUMP_FILE}"
echo
RETRY_NUM=0;
while ! $BIN_PATH/db_dump.sh > "${DB_DUMP_FILE}"; do
    echo " > dump failed, Retry `expr ${RETRY_NUM} + 1`/${MAX_RETRIES}"
    RETRY_NUM=`expr $RETRY_NUM + 1`
    if [ "${RETRY_NUM}" == "${MAX_RETRIES}" ]; then
        echo " > Retried ${MAX_RETRIES} times, giving up"
        exit 1
    fi
    echo " > retrying again in ${SECONDS_BETWEEN_RETRIES} seconds"
    echo
    sleep "${SECONDS_BETWEEN_RETRIES}"
done

exit 0
