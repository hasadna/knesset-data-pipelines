#!/usr/bin/env bash

bin/k8s_connect.sh

set -e

kubectl apply -f devops/k8s_configmap.yaml
