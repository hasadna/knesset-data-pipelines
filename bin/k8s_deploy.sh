#!/usr/bin/env bash

set -e

echo " > Applying configurations"
bin/k8s_apply.sh

echo " > waiting 10 seconds"  # for deployment to complete and to make sure we check the status of the new deployment
sleep 10

echo " > Waiting for successful rollout status"
kubectl rollout status -w deployment/app
kubectl rollout status -w deployment/db
kubectl rollout status -w deployment/nginx
