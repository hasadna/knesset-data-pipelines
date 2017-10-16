#!/usr/bin/env bash

if [ "${SERVICE_ACCOUNT_B64_JSON_SECRET_KEY}" == "" ]; then
    echo " > must set SERVICE_ACCOUNT_B64_JSON_SECRET_KEY to contain b64 encoded gcloud service account key"
    exit 2
fi

source "devops/k8s/.env.${K8S_ENVIRONMENT}" > /dev/null

export SERVICE_ACCOUNT_NAME="kdp-${K8S_ENVIRONMENT}-deployment"
export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"

echo "${SERVICE_ACCOUNT_B64_JSON_SECRET_KEY}" | base64 --d > gcloud.json
if ! gcloud auth activate-service-account "${SERVICE_ACCOUNT_ID}" --key-file gcloud.json; then
    echo " > Failed to authenticate with service account ${SERVICE_ACCOUNT_ID} using json secret key"
    rm gcloud.json
    exit 4
fi
rm gcloud.json

if ! gcloud container clusters get-credentials "${CLOUDSDK_CONTAINER_CLUSTER}"; then
    echo " > Failed to get kubernetes cluster credentials"
    exit 5
fi

if ! source bin/k8s_connect.sh; then
    echo " > Failed to connect to ${K8S_ENVIRONMENT}"
    exit 6
fi

IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-app"
if [ -f "${IID_FILE}" ]; then
    OLD_APP_IID=`cat "${IID_FILE}"`
else
    OLD_APP_IID=""
fi

if ! bin/k8s_build_push.sh --app; then
    echo " > Failed to build/push app"
    exit 7
fi

NEW_APP_IID=`cat "${IID_FILE}"`

echo " > upgrading helm"
if ! bin/k8s_helm_upgrade.sh; then
    echo " > Failed helm upgrade"
    exit 12
fi

#if [ "${OLD_APP_IID}" != "${NEW_APP_IID}" ]; then
#    echo " > detected changes in app image - ensuring app deployment will be updated"
#fi

echo " > Deployment complete!"

exit 0
