#!/usr/bin/env bash

# upgrade the helm release
# depending on the changes made - you might need to perform additional actions to complete the deployment
# see devops/k8s/README.md for more details

source bin/k8s_connect.sh
source bin/k8s_recreate_templates.sh


ENVIRONMENT_VALUES_FILE_PARAM=`[ -f "devops/k8s/values-${K8S_ENVIRONMENT}.yaml" ] && echo "-fdevops/k8s/values-${K8S_ENVIRONMENT}.yaml"`
IMAGES_VALUES_FILE_PARAM="-fdevops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"
IMAGE_APP="devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml"
IMAGE_COMMITTEES="devops/k8s/values-${K8S_ENVIRONMENT}-image-committees.yaml"
IMAGE_DB_BACKUP="devops/k8s/values-${K8S_ENVIRONMENT}-image-db-backup.yaml"

helm upgrade --timeout=5 --install --debug \
    ${ENVIRONMENT_VALUES_FILE_PARAM} \
    `test -f "${IMAGE_APP}" && echo "-f${IMAGE_APP}"` \
    `test -f "${IMAGE_COMMITTEES}" && echo "-f${IMAGE_COMMITTEES}"` \
    `test -f "${IMAGE_DB_BACKUP}" && echo "-f${IMAGE_DB_BACKUP}"` \
    knesset-data-pipelines devops/k8s $*\
    || exit 1

echo " > Helm upgrade complete"
echo
echo " > Pay attention that this doesn't necesarily mean deployment is complete"
echo
echo " > if you don't care about ~30 seconds of down-time, run bin/k8s_hard_reset.sh"
