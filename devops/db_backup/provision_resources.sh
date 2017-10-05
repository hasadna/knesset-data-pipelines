#!/usr/bin/env bash

if [ "${1}" == "" ] || [ "${2}" == "" ]; then
    echo "provision all required google cloud resources to handle db backup and restore"
    echo "usage: devops/db_backup/provision_resources.sh <SERVICE_ACCOUNT_NAME> <STORAGE_BUCKET_NAME>"
    exit 1
fi

if [ "${CLOUDSDK_CORE_PROJECT}" == "" ] || [ "${CLOUDSDK_COMPUTE_ZONE}" == "" ]; then
    echo " > Please set CLOUDSDK_CORE_PROJECT and CLOUDSDK_COMPUTE_ZONE environment variables for your google project"
    exit 2
fi

export SERVICE_ACCOUNT_NAME="${1}"
export STORAGE_BUCKET_NAME="${2}"
export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"
export SECRET_TEMPDIR="${SECRET_TEMPDIR:-`mktemp -d`}"

echo " > creating service account ${SERVICE_ACCOUNT_NAME}" >&2
gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" >&2

echo " > storing secret key at ${SECRET_TEMPDIR}/key" >&2
gcloud iam service-accounts keys create "--iam-account=${SERVICE_ACCOUNT_ID}" "${SECRET_TEMPDIR}/key" >&2

echo " > creating storage bucket gs://${STORAGE_BUCKET_NAME}" >&2
gsutil mb "gs://${STORAGE_BUCKET_NAME}" >&2 || true

echo " > setting minimal required permissions for the service account on the bucket" >&2
gsutil iam ch -d "serviceAccount:${SERVICE_ACCOUNT_ID}" "gs://${STORAGE_BUCKET_NAME}" >&2
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT_ID}:objectCreator,objectViewer,objectAdmin" "gs://${STORAGE_BUCKET_NAME}" >&2

echo " > done" >&2

echo "export SECRET_KEY_FILE=${SECRET_TEMPDIR}/key"
echo "export SERVICE_ACCOUNT_NAME=${SERVICE_ACCOUNT_NAME}"
echo "export SERVICE_ACCOUNT_ID=${SERVICE_ACCOUNT_ID}"
echo "export STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME}"
echo "export CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}"
echo "export CLOUDSDK_COMPUTE_ZONE=${CLOUDSDK_COMPUTE_ZONE}"
