#!/usr/bin/env bash

echo " > renaming environment ${K8S_ENVIRONMENT} to ${1}"
read -p "Press [Enter] to continue..."

mv "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" "devops/k8s/secrets.env.${1}"
mv "devops/k8s/.env.${K8S_ENVIRONMENT}" "devops/k8s/.env.${1}"
mv "devops/k8s/provision-values-${K8S_ENVIRONMENT}" "devops/k8s/provision-values-${1}"
