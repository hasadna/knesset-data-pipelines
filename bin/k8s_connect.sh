#!/usr/bin/env bash

# switch to the correct kubernetes cluster - be sure to run this before any other k8s command

set -e

if ! kubectl config use-context gke_hasadna-oknesset_us-central1-a_hasadna-oknesset; then
    gcloud container clusters get-credentials \
        hasadna-oknesset \
        --zone us-central1-a \
        --project hasadna-oknesset
fi
