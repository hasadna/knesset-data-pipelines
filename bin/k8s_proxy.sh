#!/usr/bin/env bash

# starts a proxy to the kubernetes cluster
# you can then goto http://localhost:8001/ui

bin/k8s_connect.sh

kubectl proxy
