#!/usr/bin/env bash

set -e

source bin/k8s_connect.sh
if ! which helm; then
    echo "Trying to install the helm binary"
    bin/install_helm.sh
fi
kubectl apply -f devops/k8s/tiller.yaml

echo " > creating secrets"
bin/k8s_recreate_secrets.sh

echo " > deploy"
bin/k8s_helm_deploy.sh
