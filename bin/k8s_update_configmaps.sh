#!/usr/bin/env bash

# update the configmap to the cluster

set -e

bin/k8s_connect.sh

kubectl apply -f devops/k8s_configmap.yaml
