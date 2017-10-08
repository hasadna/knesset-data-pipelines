#!/usr/bin/env bash

set -e

if [ "${CLOUDSDK_CORE_PROJECT}" == "" ] || [ "${CLOUDSDK_COMPUTE_ZONE}" == "" ]; then
    echo " > you must set CLOUDSDK_CORE_PROJECT and CLOUDSDK_COMPUTE_ZONE environment variables"
    exit 1
else
    echo " > Using google project id ${CLOUDSDK_CORE_PROJECT} zone ${CLOUDSDK_COMPUTE_ZONE}"
    export CLOUDSDK_CORE_PROJECT="${CLOUDSDK_CORE_PROJECT}"
    export CLOUDSDK_COMPUTE_ZONE="${CLOUDSDK_COMPUTE_ZONE}"
fi

export SERVICE_ACCOUNT_NAME="knesset-data-db-backup-test"
export STORAGE_BUCKET_NAME=knesset-data-pipelines-db-backup-test
export SERVER_CONTAINER="knesset-data-pipelines-db-dump-test-server"
export CLIENT_CONTAINER="knesset-data-pipelines-db-dump-test-client"

devops/db_backup/cleanup_resources.sh $SERVICE_ACCOUNT_NAME $STORAGE_BUCKET_NAME > /dev/null 2>&1 || true
docker rm --force $SERVER_CONTAINER > /dev/null 2>&1 || true
docker rm --force $CLIENT_CONTAINER > /dev/null 2>&1 || true
rm knesset-data-pipelines-test-client-log > /dev/null 2>&1 || true

sleep 2

echo " > provisioning resources"
source <(devops/db_backup/provision_resources.sh $SERVICE_ACCOUNT_NAME $STORAGE_BUCKET_NAME)
echo " > done, SECRET_KEY_FILE=${SECRET_KEY_FILE}"

echo " > running db server"
docker run --rm -d --name "${SERVER_CONTAINER}" \
    -p "5432:5432" \
    -e POSTGRES_PASSWORD=123456 \
    postgres:alpine

echo " > sleeping 10 seconds to let db server start"
sleep 10

echo " > creating foobarbaz database and inserting a row"
docker exec "${SERVER_CONTAINER}" su-exec postgres psql -c "create database foobarbaz"
docker exec "${SERVER_CONTAINER}" su-exec postgres psql -c "create table foo (bar integer)"
docker exec "${SERVER_CONTAINER}" su-exec postgres psql -c "insert into foo values (123)"

echo " > running db backup"
docker build -t db_backup_test devops/db_backup && docker run --rm --name "${CLIENT_CONTAINER}" \
    --link "${SERVER_CONTAINER}" \
    -e "PGPASSWORD=123456" \
    -e "PGHOST=${SERVER_CONTAINER}" \
    -e "PGPORT=5432" \
    -e "PGUSER=postgres" \
    -e "GOOGLE_AUTH_SECRET_KEY_FILE=/secret/key" \
    -e "SERVICE_ACCOUNT_ID=${SERVICE_ACCOUNT_ID}" \
    -e "CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}" \
    -e "CLOUDSDK_COMPUTE_ZONE=${CLOUDSDK_COMPUTE_ZONE}" \
    -e "STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME}" \
    -e "BACKUP_INITIAL_DELAY_SECONDS=1" \
    -e "BACKUP_FILE_TEMPLATE=test-backup" \
    -v "${SECRET_TEMPDIR}:/secret" \
    db_backup_test 2>&1 | tee knesset-data-pipelines-test-client-log &

echo " > waiting 10 seconds for db dump to complete"
sleep 10

echo " > copy dump file from the container filesystem"
docker cp "${CLIENT_CONTAINER}:/dump.sql" devops/db_backup/knesset-data-pipelines-test-dump.sql

echo " > stopping the db backup container"
docker stop "${CLIENT_CONTAINER}"

echo " > testing db backup"

if ! cat knesset-data-pipelines-test-client-log | grep "Uploaded db backup to gs://${STORAGE_BUCKET_NAME}/test-backup.sql"; then
    echo " > Looks like upload failed"
    exit 1
fi

if ! gsutil stat "gs://${STORAGE_BUCKET_NAME}/test-backup.sql"; then
    echo " > Couldn't find uploaded dump in gs://${STORAGE_BUCKET_NAME}/test-backup.sql"
    exit 1
fi

if ! gsutil cat "gs://${STORAGE_BUCKET_NAME}/test-backup.sql" | grep "CREATE DATABASE foobarbaz"; then
    echo " > dump file exists, but doesn't seem to contain a DB dump"
    exit 1
fi

echo " > deleting test db - to ensure we really restore"
docker exec "${SERVER_CONTAINER}" su-exec postgres psql -c "drop database foobarbaz"
if docker exec "${SERVER_CONTAINER}" su-exec postgres psql -Atc "select * from foobarbaz.foo"; then
    echo " > test db exists - cannot test restore"
    exit 1
fi

echo " > running db restore"
docker run --rm --name "${CLIENT_CONTAINER}" \
    --link "${SERVER_CONTAINER}" \
    -e "PGPASSWORD=123456" \
    -e "PGHOST=${SERVER_CONTAINER}" \
    -e "PGPORT=5432" \
    -e "PGUSER=postgres" \
    -e "GOOGLE_AUTH_SECRET_KEY_FILE=/secret/key" \
    -e "SERVICE_ACCOUNT_ID=${SERVICE_ACCOUNT_ID}" \
    -e "CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}" \
    -e "CLOUDSDK_COMPUTE_ZONE=${CLOUDSDK_COMPUTE_ZONE}" \
    -e "STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME}" \
    -e "BACKUP_INITIAL_DELAY_SECONDS=1" \
    -e "BACKUP_FILE_TEMPLATE=test-backup" \
    -e "RESTORE_GS_URL=gs://${STORAGE_BUCKET_NAME}/test-backup.sql" \
    -v "${SECRET_TEMPDIR}:/secret" \
    db_backup_test 2>&1 | tee knesset-data-pipelines-test-client-log & sleep 5 && docker stop "${CLIENT_CONTAINER}"

echo " > testing db restore"

if ! docker exec "${SERVER_CONTAINER}" su-exec postgres psql -Atc "select * from foo" | grep "123"; then
    echo " > db restore failed"
    exit 1
fi

echo " > Done, cleaning up..."
devops/db_backup/cleanup_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}" "${SECRET_TEMPDIR}" || true
rm -f knesset-data-pipelines-test-client-log

echo
echo " > The test completed successfully!"
echo
exit 0
