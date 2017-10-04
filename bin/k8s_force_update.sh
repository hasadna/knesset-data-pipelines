#!/usr/bin/env bash

# force an update for a K8S deployment by setting a label with unix timestamp

source bin/k8s_connect.sh

if [ "${1}" == "" ]; then
    echo "usage: bin/k8s_force_update.sh <deployment_name>"
    exit 1
else
    kubectl patch deployment "${1}" -p "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"date\":\"`date +'%s'`\"}}}}}"
    kubectl rollout status deployment "${1}"
    exit 0
fi
