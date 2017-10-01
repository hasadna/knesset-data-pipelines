#!/usr/bin/env bash

if [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

if [ "${K8S_ENVIRONMENT}" != "staging" ]; then
    echo " > only staging environment is supported"
    exit 1
fi

if [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    echo "destroy the existing cluster first by running bin/k8s_destroy.sh"
    exit 1
fi

echo " > Will create a new staging cluster, this might take a while..."
echo "You should have a Google project ID with active billing"
echo "Staging cluster will comprise of 3 g1-small machines (shared vCPU, 1.70GB ram)"
echo "We also utilize some other resources which are negligable"
echo "Total cluster cost shouldn't be more then ~0.09 USD per hour"
echo "When done, run bin/k8s_destroy.sh to ensure cluster is destroyed and billing will stop"
read -p "Enter your authenticated, billing activated, Google project id: " GCLOUD_PROJECT_ID

echo " > Creating devops/k8s/.env.staging file"
echo "export K8S_ENVIRONMENT=staging" >> devops/k8s/.env.staging
echo "export CLOUDSDK_CORE_PROJECT=${GCLOUD_PROJECT_ID}" >> devops/k8s/.env.staging
echo "export CLOUDSDK_COMPUTE_ZONE=us-central1-a" >> devops/k8s/.env.staging
echo "export CLOUDSDK_CONTAINER_CLUSTER=knesset-data-pipelines" >> devops/k8s/.env.staging
source devops/k8s/.env.staging

echo " > Creating persistent disks"
gcloud compute disks create --size=5GB "knesset-data-pipelines-${K8S_ENVIRONMENT}-db"
gcloud compute disks create --size=5GB "knesset-data-pipelines-${K8S_ENVIRONMENT}-app"

echo " > Creating the cluster"
gcloud container clusters create $CLOUDSDK_CONTAINER_CLUSTER \
    --disk-size=20 \
    --no-enable-cloud-logging --no-enable-cloud-monitoring \
    --machine-type=g1-small \
    --num-nodes=3

echo " > Adding the kube context to the env file"
gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER
echo "kubectl config use-context `kubectl config current-context`" >> devops/k8s/.env.staging

echo " > Done, cluster is ready"
echo "next step is deployment: bin/k8s_deploy.sh"
