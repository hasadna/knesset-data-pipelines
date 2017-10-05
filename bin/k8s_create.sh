#!/usr/bin/env bash

# creates and configures a knesset-data-pipelines Kubernetes cluster and related resources on Google cloud

if [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

if [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    if [ "${1}" == "--force" ]; then
        echo " > Deleting existing env file: devops/k8s/.env.${K8S_ENVIRONMENT}"
        read -p "Are you sure you want to continue? [y/N] "
        if [ "${REPLY}" == "y" ]; then
            rm "devops/k8s/.env.${K8S_ENVIRONMENT}"
        else
            exit 1
        fi
    else
        echo "destroy the existing cluster first by running bin/k8s_destroy.sh"
        echo "alternatively - run bin/k8s_create.sh --force"
        exit 1
    fi
fi

echo " > Will create a new staging cluster, this might take a while..."
echo "You should have a Google project ID with active billing"
echo "Staging cluster will comprise of 3 g1-small machines (shared vCPU, 1.70GB ram)"
echo "We also utilize some other resources which are negligable"
echo "Total cluster cost shouldn't be more then ~0.09 USD per hour"
echo "When done, run bin/k8s_destroy.sh to ensure cluster is destroyed and billing will stop"
read -p "Enter your authenticated, billing activated, Google project id: " GCLOUD_PROJECT_ID

echo " > Creating devops/k8s/.env.${K8S_ENVIRONMENT} file"
echo "export K8S_ENVIRONMENT=${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
echo "export CLOUDSDK_CORE_PROJECT=${GCLOUD_PROJECT_ID}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
echo "export CLOUDSDK_COMPUTE_ZONE=us-central1-a" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
echo "export CLOUDSDK_CONTAINER_CLUSTER=knesset-data-pipelines-${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
source "devops/k8s/.env.${K8S_ENVIRONMENT}"

echo " > Creating the cluster"
bin/k8s_provision.sh cluster

echo " > Creating persistent disks"
bin/k8s_provision.sh db
bin/k8s_provision.sh app

echo " > Done, cluster is ready"
echo "next step is deployment: bin/k8s_deploy.sh"
