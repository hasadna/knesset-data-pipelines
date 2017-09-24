#!/usr/bin/env bash

# apply all configuration changes to the kubernetes cluster

set -e

bin/k8s_connect.sh

kubectl apply -f devops/k8s/adminer.yaml \
              -f devops/k8s/app.yaml \
              -f devops/k8s/db.yaml \
              -f devops/k8s/flower.yaml \
              -f devops/k8s/letsencrypt.yaml \
              -f devops/k8s/nginx.yaml \
              -f devops/k8s/redis.yaml \
              -f devops/k8s/metabase.yaml
