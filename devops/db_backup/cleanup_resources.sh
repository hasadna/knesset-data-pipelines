#!/usr/bin/env bash

if [ "${1}" == "" ]; then
    echo "cleanup all resources created by provision_resources"
    echo "usage: devops/db_backup/cleanup_resources.sh <SERVICE_ACCOUNT_NAME> [STORAGE_BUCKET_NAME] [SECRET_TEMPDIR]"
    exit 1
fi

if [ "${CLOUDSDK_CORE_PROJECT}" == "" ] || [ "${CLOUDSDK_COMPUTE_ZONE}" == "" ]; then
    echo " > Please set CLOUDSDK_CORE_PROJECT and CLOUDSDK_COMPUTE_ZONE environment variables for your google project"
    exit 2
fi

export SERVICE_ACCOUNT_NAME="${1}"
export STORAGE_BUCKET_NAME="${2}"
export SECRET_TEMPDIR="${3}"
export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"

echo " > Deleting service account"
gcloud iam service-accounts delete --quiet "${SERVICE_ACCOUNT_ID}" || exit 3

if [ "${STORAGE_BUCKET_NAME}" != "" ]; then
    echo " > Removing storage bucket"
    gsutil rb "gs://${STORAGE_BUCKET_NAME}" || exit 5
fi

if [ "${SECRET_TEMPDIR}" != "" ]; then
    echo " > Removing secret tempdir"
    rm -rf "${SECRET_TEMPDIR}" || exit 4
fi

echo " > done"
exit 0
