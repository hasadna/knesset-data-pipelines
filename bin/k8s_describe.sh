#!/usr/bin/env bash

# shows some useful details about the kubernetes nodes

bin/k8s_connect.sh

kubectl describe "${1:-nodes}"
