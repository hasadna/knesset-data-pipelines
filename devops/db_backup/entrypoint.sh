#!/usr/bin/env bash

# Postgresql environment variables - used by pg_dumpall to dump all databases
# we use the default Postgresql client environment variables to connect
# see https://www.postgresql.org/docs/current/static/libpq-envars.html
# Usually you will want to set the following:
# PGPASSWORD - Postgresql password
# PGHOST - Postgresql host name
# PGPORT - Postgresql port
# PGUSER - Postgresql user

# Google Cloud environment variables - used to upload the dumps to google storage
# GOOGLE_AUTH_SECRET_KEY_FILE - path to secret key for authentication (populated using K8S secret)
# SERVICE_ACCOUNT_ID - Google cloud service account id
# CLOUDSDK_CORE_PROJECT - Google cloud project id
# CLOUDSDK_COMPUTE_ZONE - Google cloud zone
# STORAGE_BUCKET_NAME - Google cloud storage bucket name (should be created beforehand)

# Backup related environment variables
# BACKUP_INTERVAL_SECONDS - how many seconds to wait between backups (default = 86400 = 1 day)
# BACKUP_INITIAL_DELAY_SECONDS - when first starting - how long to wait before doing the first backup (default = 15 seconds)
# BACKUP_MAX_RETRIES = (default=5)
# BACKUP_SECONDS_BETWEEN_RETRIES (default=5)
# BACKUP_FILE_TEMPLATE = (default=%y-%m-%d-%H-%M)

trap "exit 1" SIGTERM;
trap "exit 2" SIGINT;

db_dump_retry() {
    local DB_DUMP_FILE="${1}"
    local RETRY_NUM=0;
    local MAX_RETRIES=${BACKUP_MAX_RETRIES:-5}
    local SECONDS_BETWEEN_RETRIES=${BACKUP_SECONDS_BETWEEN_RETRIES:-5}
    echo " > Creating DB dump ${DB_DUMP_FILE}"
    echo
    while ! pg_dumpall > "${DB_DUMP_FILE}"; do
        echo " > dump failed, Retry `expr ${RETRY_NUM} + 1`/${MAX_RETRIES}"
        RETRY_NUM=`expr $RETRY_NUM + 1`
        if [ "${RETRY_NUM}" == "${MAX_RETRIES}" ]; then
            echo " > Retried ${MAX_RETRIES} times, giving up"
            return 1
        fi
        echo " > retrying again in ${SECONDS_BETWEEN_RETRIES} seconds"
        echo
        sleep "${SECONDS_BETWEEN_RETRIES}"
    done
    return 0
}

google_storage_upload() {
    UPLOAD_FILE="${1}"
    UPLOAD_TARGET_URL="gs://${STORAGE_BUCKET_NAME}/`date +${BACKUP_FILE_TEMPLATE:-%y-%m-%d-%H-%M}`.sql"
    if [ -f "${UPLOAD_FILE}" ]; then
        echo " > authenticating with google using service account ${SERVICE_ACCOUNT_ID}";
        if ! gcloud auth activate-service-account "${SERVICE_ACCOUNT_ID}" --key-file "${GOOGLE_AUTH_SECRET_KEY_FILE}"; then
            echo " > Failed to authenticate with google cloud using keyfile ${GOOGLE_AUTH_SECRET_KEY_FILE}"
            return 1
        fi
        echo " > uploading from ${UPLOAD_FILE} to ${UPLOAD_TARGET_URL}"
        if ! gsutil cp "${UPLOAD_FILE}" "${UPLOAD_TARGET_URL}"; then
            echo " > Upload failed"
            return 2
        fi
        echo " > Upload succeeded"
        return 0
    else
        echo " > dbdump file was not found";
        return 0
    fi
}

echo " > sleeping ${BACKUP_INITIAL_DELAY_SECONDS:-15} seconds to allow DB to start properly";
sleep "${BACKUP_INITIAL_DELAY_SECONDS:-15}";
while true; do
    if ! db_dump_retry /dbdump.sql; then
        echo " > Exiting due to db dump failure"
        exit 1
    fi
    if ! google_storage_upload /dbdump.sql; then
        echo " > EXiting due to google storage upload failure"
        exit 1
    fi
    echo " > sleeping ${BACKUP_INTERVAL_SECONDS:-86400} seconds until next backup";
    sleep "${BACKUP_INTERVAL_SECONDS:-86400}";
done
