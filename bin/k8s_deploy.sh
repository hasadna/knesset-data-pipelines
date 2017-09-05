#!/usr/bin/env bash

if [ "${1}" == "" ] || [ "${2}" == "" ]; then
    echo "usage: bin/k8s_deploy.sh <deploynemt_name> <image_suffix>"
else
    kubectl set image "deployment/${1}" "${1}=gcr.io/hasadna-oknesset/knesset-data-${2}" && kubectl rollout status "deployment/${1}"
fi
