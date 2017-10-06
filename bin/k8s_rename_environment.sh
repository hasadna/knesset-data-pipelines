#!/usr/bin/env bash

echo " > renaming environment ${K8S_ENVIRONMENT} to ${1}"
read -p "Press [Enter] to continue..."

mv "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" "devops/k8s/secrets.env.${1}"
mv "devops/k8s/.env.${K8S_ENVIRONMENT}" "devops/k8s/.env.${1}"
mv "devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml" "devops/k8s/values-${1}-image-app.yaml"
mv "devops/k8s/values-${K8S_ENVIRONMENT}-image-committees.yaml" "devops/k8s/values-${1}-image-committees.yaml"
mv "devops/k8s/values-${K8S_ENVIRONMENT}-image-db-backup.yaml" "devops/k8s/values-${1}-image-db-backup.yaml"
mv "devops/k8s/provision-values-${K8S_ENVIRONMENT}" "devops/k8s/provision-values-${1}"
