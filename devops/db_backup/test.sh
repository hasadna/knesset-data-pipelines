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
export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"
export SECRET_TEMPDIR=`mktemp -d`
export STORAGE_BUCKET_NAME=knesset-data-pipelines-db-backup-test
export SERVER_CONTAINER="knesset-data-pipelines-db-dump-test-server"
export CLIENT_CONTAINER="knesset-data-pipelines-db-dump-test-client"

cleanup() {
    echo "> Stopping DB server"
    docker stop "${SERVER_CONTAINER}" || true
    docker stop "${CLIENT_CONTAINER}" || true

    echo " > Deleting service account"
    gcloud iam service-accounts delete --quiet "${SERVICE_ACCOUNT_ID}" || true
    echo " > Removing secrets"
    rm -rf "${SECRET_TEMPDIR}" || true
    echo " > Removing file from bucket (but keeping the bucket..)"
    gsutil rm "gs://${STORAGE_BUCKET_NAME}/test-backup.sql" || true
    echo " > Removing temporary files"
    rm knesset-data-pipelines-test-client-log || true
}

cleanup
sleep 2

gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}"
gcloud iam service-accounts keys create "--iam-account=${SERVICE_ACCOUNT_ID}" "${SECRET_TEMPDIR}/key"
gsutil mb "gs://${STORAGE_BUCKET_NAME}/" || gsutil rm "gs://${STORAGE_BUCKET_NAME}/test-backup.sql" || true
gsutil iam ch -d "serviceAccount:${SERVICE_ACCOUNT_ID}" "gs://${STORAGE_BUCKET_NAME}"
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT_ID}:objectCreator,objectViewer,objectAdmin" "gs://${STORAGE_BUCKET_NAME}"

docker run --rm -d --name "${SERVER_CONTAINER}" \
    -p "5432:5432" \
    -e POSTGRES_PASSWORD=123456 \
    postgres:alpine
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
    db_backup_test 2>&1 | tee knesset-data-pipelines-test-client-log & sleep 20 && docker stop "${CLIENT_CONTAINER}"

if ! cat knesset-data-pipelines-test-client-log | grep "Upload succeeded"; then
    echo " > Looks like upload failed"
    exit 1
fi

if ! gsutil stat "gs://${STORAGE_BUCKET_NAME}/test-backup.sql"; then
    echo " > Couldn't find uploaded dump in gs://${STORAGE_BUCKET_NAME}/test-backup.sql"
    exit 1
fi

if ! gsutil cat "gs://${STORAGE_BUCKET_NAME}/test-backup.sql" | grep "PostgreSQL database cluster dump"; then
    echo " > dump file exists, but doesn't seem to contain a DB dump"
    exit 1
fi

echo " > Done, cleaning up..."

cleanup
exit 0
