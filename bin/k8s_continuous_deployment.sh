#!/usr/bin/env bash

if [ "${SERVICE_ACCOUNT_B64_JSON_SECRET_KEY}" == "" ]; then
    echo " > must set SERVICE_ACCOUNT_B64_JSON_SECRET_KEY to contain b64 encoded gcloud service account key"
    exit 2
fi

source "devops/k8s/.env.${K8S_ENVIRONMENT}" > /dev/null

export SERVICE_ACCOUNT_NAME="kdp-${K8S_ENVIRONMENT}-deployment"
export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"

echo "${SERVICE_ACCOUNT_B64_JSON_SECRET_KEY}" | base64 --d > gcloud.json
if ! gcloud auth activate-service-account "${SERVICE_ACCOUNT_ID}" --key-file gcloud.json; then
    echo " > Failed to authenticate with service account ${SERVICE_ACCOUNT_ID} using json secret key"
    rm gcloud.json
    exit 4
fi
rm gcloud.json

if ! gcloud container clusters get-credentials "${CLOUDSDK_CONTAINER_CLUSTER}"; then
    echo " > Failed to get kubernetes cluster credentials"
    exit 5
fi

if ! source bin/k8s_connect.sh; then
    echo " > Failed to connect to ${K8S_ENVIRONMENT}"
    exit 6
fi

if [ "${K8S_CD_AUTOSCALER}" == "1" ]; then
    echo " > autoscaler initialized action - skipping app build/push"
else
    echo " > building and pushing app image"
    IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-app"
    if [ -f "${IID_FILE}" ]; then
        OLD_APP_IID=`cat "${IID_FILE}"`
    else
        OLD_APP_IID=""
    fi
    if ! bin/k8s_build_push.sh --app; then
        echo " > Failed to build/push app"
        exit 7
    fi
    NEW_APP_IID=`cat "${IID_FILE}"`
    if [ "${OLD_APP_IID}" != "${NEW_APP_IID}" ]; then
        echo " > changed detected in app iid file, forcing upgrade of workers"
        K8S_UPGRADE_WORKERS="1"
    fi
fi

if [ "${K8S_UPGRADE_WORKERS}" == "1" ]; then
    echo " > scaling down worker pods (to reduce CPU load while deploying)"
    kubectl scale --replicas=0 deployment/app-idle-worker
    DPP_WORKERS_NODES=`kubectl get nodes | tee /dev/stderr | grep -- -dpp-workers- | cut -d" " -f1 -`
    if [ "${DPP_WORKER_NODES}" != "" ]; then
        echo " > draining dpp-workers nodes"
        kubectl scale --replicas=0 deployment/app-workers
        for NODE in `kubectl get nodes | grep -- -dpp-workers- | cut -d" " -f1 -`; do
            kubectl drain "${NODE}" --force --ignore-daemonsets
        done
    fi
fi

echo " > upgrading helm"
if ! bin/k8s_helm_upgrade.sh; then
    echo " > Failed helm upgrade"
    exit 12
fi

if [ "${K8S_UPGRADE_WORKERS}" == "1" ]; then
    echo " > scaling workers back up"
    kubectl scale --replicas=1 deployment/app-idle-worker
    DPP_WORKERS_NODES=`kubectl get nodes | tee /dev/stderr | grep -- -dpp-workers- | cut -d" " -f1 -`
    if [ "${DPP_WORKER_NODES}" != "" ] &&\
       [ `bin/read_yaml.py devops/k8s/values-${K8S_ENVIRONMENT}-provision.yaml app enableWorkers` == "True" ]
    then
        echo " > uncordoning dpp-workers nodes"
        kubectl scale --replicas=2 deployment/app-workers
        for NODE in `kubectl get nodes | grep -- -dpp-workers- | cut -d" " -f1 -`; do
            kubectl uncordon "${NODE}" --force --ignore-daemonsets
        done
    fi
fi

if [ `bin/read_yaml.py devops/k8s/values-${K8S_ENVIRONMENT}-provision.yaml app enableAutoscaler` == "True" ]; then
    if [ `bin/read_yaml.py devops/k8s/values-${K8S_ENVIRONMENT}-provision.yaml app enableWorkers` == "True" ]; then
        if [ `kubectl get nodes | grep gke- | grep dpp-workers | wc -l` == "0" ]; then
            echo " > workers are enabled, but no worker nodes found, provisioning dpp-workers"
            bin/k8s_provision.sh dpp-workers
            sleep 15
        fi
    elif [ `kubectl get nodes | grep gke- | grep dpp-workers | wc -l` != "0" ]; then
        echo " > workers are disabled, but worker nodes found, deleting dpp-worker nodes"
        bin/k8s_provision.sh dpp-workers --delete
        sleep 15
    fi
fi

echo " > Deployment complete!"

exit 0
