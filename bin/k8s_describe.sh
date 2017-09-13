#!/usr/bin/env bash

bin/k8s_connect.sh

kubectl describe "${1:-nodes}"
