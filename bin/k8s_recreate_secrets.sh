#!/usr/bin/env bash

# apply the secrets to the K8S cluster of the current environment

source bin/k8s_connect.sh

echo " > recreating secrets for ${K8S_ENVIRONMENT} environment"

if [ ! -f devops/k8s/secrets.env.${K8S_ENVIRONMENT} ]; then
    echo " > missing devops/k8s/secrets.env.${K8S_ENVIRONMENT} file - cannot create k8s secrets"
    exit 1
fi

kubectl delete secret env-vars

while ! timeout 4s kubectl create secret generic env-vars --from-env-file devops/k8s/secrets.env.${K8S_ENVIRONMENT}; do
    sleep 1
done

exit 0
