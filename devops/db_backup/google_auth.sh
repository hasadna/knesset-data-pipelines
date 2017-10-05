#!/usr/bin/env bash

echo " > authenticating with google using service account ${SERVICE_ACCOUNT_ID}";

if [ "${GOOGLE_AUTH_SECRET_KEY_B64_JSON}" != "" ]; then
    echo " > authenticating with inline base 64 encoded json key"
    export GOOGLE_AUTH_SECRET_KEY_FILE="/secret-key"
    echo "${GOOGLE_AUTH_SECRET_KEY_B64_JSON}" | base64 -d > "${GOOGLE_AUTH_SECRET_KEY_FILE}"
fi

if ! gcloud auth activate-service-account "${SERVICE_ACCOUNT_ID}" --key-file "${GOOGLE_AUTH_SECRET_KEY_FILE}"; then
    echo " > Failed to authenticate with google cloud using keyfile ${GOOGLE_AUTH_SECRET_KEY_FILE}"
    exit 1
fi

exit 0
