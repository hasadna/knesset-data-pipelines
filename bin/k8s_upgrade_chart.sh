#!/usr/bin/env bash

# upgrade the helm release
# depending on the changes made - you might need to perform additional actions to complete the deployment
# see devops/k8s/README.md for more details

source bin/k8s_connect.sh > /dev/null

VALUE_ARGS=""
for FILE in `ls devops/k8s/values-${K8S_ENVIRONMENT}-*.yaml`; do
    VALUE_ARGS+=" -f${FILE}"
done

helm upgrade ${VALUE_ARGS} "$@"
