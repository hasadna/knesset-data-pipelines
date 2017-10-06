#!/usr/bin/env bash

# stop all pods in the K8S cluster and start them in correct order, ensuring that environment is fully restarted

source bin/k8s_connect.sh > /dev/null

if [ "${K8S_ENVIRONMENT}" != "staging" ]; then
    echo "hard reset is only supported on staging environment"
    exit 1
fi

scale_down() {
    echo " > Scaling down $1 to 0 replicas"
    if ! kubectl scale deployment $1 --replicas=0; then
        exit 1
    fi
}

scale_up() {
    echo " > Scaling up $1 to 1 replicas"
    if ! kubectl scale deployment $1 --replicas=1; then
        exit 1
    fi
}

echo " > The hard reset procedure will have some down-time"
read -p "Are you sure you want to continue? [y/N] "
if [ "${REPLY}" != "y" ]; then
    exit 1
fi



scale_down adminer
scale_down app
scale_down db
scale_down flower
scale_down redis

echo " > Sleeping 10 seconds to allow persistent disks to be released"
sleep 10

scale_up db
scale_up redis

echo " > Sleeping 10 seconds to allow db and redis to start"
sleep 10

scale_up adminer
scale_up app
scale_up flower

echo " > Done, all services should be active"

kubectl get deployments
kubectl get pods
