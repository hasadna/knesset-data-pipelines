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

# TODO: load them automatically from the directory, instead of one by one
PROVISION_DB_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/db.yaml"
PROVISION_APP_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/app.yaml"
PROVISION_DB_RESTORE_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/db-restore.yaml"
PROVISION_DPP_WORKERS_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/dpp-workers.yaml"
PROVISION_METABASE_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/metabase.yaml"
PROVISION_GRAFANA_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/grafana.yaml"
PROVISION_SHARED_HOST_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/shared-host.yaml"
PROVISION_NGINX_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/nginx.yaml"
PROVISION_LETSENCRYPT_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/letsencrypt.yaml"
PROVISION_COMMITTEES_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/committees.yaml"
PROVISION_DB_BACKUP_VALUES="devops/k8s/provision-values-${K8S_ENVIRONMENT}/db-backup.yaml"

helm upgrade --timeout=5 --install --debug \
    ${ENVIRONMENT_VALUES_FILE_PARAM} \
    `test -f "${IMAGE_APP}" && echo "-f${IMAGE_APP}"` \
    `test -f "${IMAGE_COMMITTEES}" && echo "-f${IMAGE_COMMITTEES}"` \
    `test -f "${IMAGE_DB_BACKUP}" && echo "-f${IMAGE_DB_BACKUP}"` \
    `test -f "${PROVISION_DB_VALUES}" && echo "-f${PROVISION_DB_VALUES}"` \
    `test -f "${PROVISION_APP_VALUES}" && echo "-f${PROVISION_APP_VALUES}"` \
    `test -f "${PROVISION_DB_RESTORE_VALUES}" && echo "-f${PROVISION_DB_RESTORE_VALUES}"` \
    `test -f "${PROVISION_DPP_WORKERS_VALUES}" && echo "-f${PROVISION_DPP_WORKERS_VALUES}"` \
    `test -f "${PROVISION_METABASE_VALUES}" && echo "-f${PROVISION_METABASE_VALUES}"` \
    `test -f "${PROVISION_GRAFANA_VALUES}" && echo "-f${PROVISION_GRAFANA_VALUES}"` \
    `test -f "${PROVISION_SHARED_HOST_VALUES}" && echo "-f${PROVISION_SHARED_HOST_VALUES}"` \
    `test -f "${PROVISION_NGINX_VALUES}" && echo "-f${PROVISION_NGINX_VALUES}"` \
    `test -f "${PROVISION_LETSENCRYPT_VALUES}" && echo "-f${PROVISION_LETSENCRYPT_VALUES}"` \
    `test -f "${PROVISION_COMMITTEES_VALUES}" && echo "-f${PROVISION_COMMITTEES_VALUES}"` \
    `test -f "${PROVISION_DB_BACKUP_VALUES}" && echo "-f${PROVISION_DB_BACKUP_VALUES}"` \
    knesset-data-pipelines devops/k8s $*\
    || exit 1

echo " > Helm upgrade complete"
echo
echo " > Pay attention that this doesn't necesarily mean deployment is complete"
echo
echo " > if you don't care about ~30 seconds of down-time, run bin/k8s_hard_reset.sh"
