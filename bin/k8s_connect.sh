#!/usr/bin/env bash

# connect to a deployment environment
# by default connects to staging, for other environments - set the K8S_ENVIRONMENT variable
# should be used by bash source - to enable bash completion and PS1 indication of environment:
# source bin/k8s_connect.sh
#
# To force re-authentication to google, run the following:
# source bin/k8s_connect.sh; rm "devops/k8s/.env.${K8S_ENVIRONMENT}"; source bin/k8s_connect.sh


if [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

if [ ! -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    echo " > Missing devops/k8s/.env.$K8S_ENVIRONMENT file, will try to create it and connect to an existing cluster"
    if [ "${CLOUDSDK_CORE_PROJECT}" != "" ]; then
        echo " > current environment CLOUDSDK_CORE_PROJECT variable value is ${CLOUDSDK_CORE_PROJECT}"
        echo " > you can type it below if that's the correct project for ${K8S_ENVIRONMENT} environment of knesset-data-pipelines project"
    fi
    read -p "Your Google project id: " CLOUDSDK_CORE_PROJECT
    echo "export K8S_ENVIRONMENT=${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_COMPUTE_ZONE=us-central1-a" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    echo "export CLOUDSDK_CONTAINER_CLUSTER=knesset-data-pipelines-${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    source "devops/k8s/.env.${K8S_ENVIRONMENT}"
    if ! gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER; then
        echo " > Failed to authenticate with google or find the cluster"
        echo " > To create a cluster, run bin/k8s_create.sh"
        echo " > To modify google / cluster connection configuration - create the env file manually using devops/k8s/.env.example"
        rm devops/k8s/.env.${K8S_ENVIRONMENT}
    else
        echo "kubectl config use-context \"gke_${CLOUDSDK_CORE_PROJECT}_${CLOUDSDK_COMPUTE_ZONE}_${CLOUDSDK_CONTAINER_CLUSTER}\"" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
    fi
fi

if [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    source "devops/k8s/.env.${K8S_ENVIRONMENT}"
    source <(kubectl completion bash)
    if [ "${KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1}" == "" ]; then
        export KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1="${PS1}"
    fi
    export PS1="${KNESSET_DATA_PIPELINES_K8S_CONNECT_ORIGINAL_PS1}\[\033[01;32m\]${K8S_ENVIRONMENT}\[\033[0m\]$ "
fi

if [ `kubectl config current-context` == "gke_${CLOUDSDK_CORE_PROJECT}_${CLOUDSDK_COMPUTE_ZONE}_${CLOUDSDK_CONTAINER_CLUSTER}" ]; then
    echo " > Connected to cluster ${CLOUDSDK_CONTAINER_CLUSTER} environment ${K8S_ENVIRONMENT}"
else
    echo " > Failed to connect! Please check devops/k8s/.env.${K8S_ENVIRONMENT} or create a new cluster using bin/k8s_create.sh --force"
    echo " > To ensure you don't use the wrong cluster, will now exit the shell session"
    read -p "Press <Enter> to continue"
    exit 1
fi
