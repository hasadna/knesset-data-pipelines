#!/usr/bin/env bash

source bin/k8s_connect.sh
source bin/k8s_recreate_templates.sh


ENVIRONMENT_VALUES=`[ -f "devops/k8s/values-${K8S_ENVIRONMENT}.yaml" ] && "devops/k8s/values-${K8S_ENVIRONMENT}.yaml"`


helm upgrade --timeout=5 --install --debug -f "devops/k8s/values-${K8S_ENVIRONMENT}.yaml" -f "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml" knesset-data-pipelines devops/k8s $* || exit 1

echo " > Helm upgrade complete"
echo
echo " > Pay attention that this doesn't necesarily mean deployment is complete"
echo
echo " > on staging environment you can run bin/k8s_hard_reset.sh to ensure deployment is complete"
