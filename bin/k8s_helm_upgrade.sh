#!/usr/bin/env bash

# upgrade the helm release
# depending on the changes made - you might need to perform additional actions to complete the deployment
# see devops/k8s/README.md for more details

source bin/k8s_connect.sh > /dev/null
source bin/k8s_recreate_templates.sh > /dev/null

VALUE_ARGS=""
for FILE in `ls devops/k8s/values-${K8S_ENVIRONMENT}-*.yaml`; do
    VALUE_ARGS+=" -f${FILE}"
done

if ! eval "helm upgrade --timeout=5 --install --debug ${VALUE_ARGS} knesset-data-pipelines devops/k8s ${*}"; then
    echo " > upgrade failed"
    exit 1
fi

echo " > Helm upgrade complete"
