#!/usr/bin/env bash

if [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

if [ ! -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    echo " > Missing devops/k8s/.env.$K8S_ENVIRONMENT file, will try to create it and connect to an existing cluster"
    read -p "Your Google Project Id: " CLOUDSDK_CORE_PROJECT
    echo "export K8S_ENVIRONMENT=${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_COMPUTE_ZONE=us-central1-a" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_CONTAINER_CLUSTER=knesset-data-pipelines-${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    source "devops/k8s/.env.${K8S_ENVIRONMENT}"
    if ! gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER; then
        echo " > Failed to authenticate with google or find the cluster"
        echo " > To create a cluster, run bin/k8s_create.sh"
        rm "devops/k8s/.env.${K8S_ENVIRONMENT}"
        exit 1
    fi
    echo "kubectl config use-context \"gke_${CLOUDSDK_CORE_PROJECT}_${CLOUDSDK_COMPUTE_ZONE}_${CLOUDSDK_CONTAINER_CLUSTER}\"" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
fi

source "devops/k8s/.env.${K8S_ENVIRONMENT}"
source <(kubectl completion bash)

if [ "${KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1}" == "" ]; then
    export KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1="${PS1}"
fi

export PS1="${KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1}\[\033[01;32m\]${K8S_ENVIRONMENT}\[\033[0m\]$ "
