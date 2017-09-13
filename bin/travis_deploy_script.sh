#!/usr/bin/env bash

# required environment variables - set via travis

# CLOUDSDK_COMPUTE_ZONE=us-central1-a
# CLOUDSDK_CORE_DISABLE_PROMPTS=1
# CLOUDSDK_CORE_PROJECT=hasadna-oknesset

# you need to add a service account
# google console web ui > IAM > service accounts > create
# give container engine roles to this account
# choose to furnish a new key and download it as json
# GCLOUD_EMAIL=oknesset-devops-deploy@hasadna-oknesset.iam.gserviceaccount.com
# to get the key, run something like this (with the downloaded json private key)
# cat ~/Downloads/OKnesset-xxx.json | base64 -w0
# GCLOUD_KEY=

# connection details to the kubernetes master

# get this using kubectl cluster-info
# GKE_SERVER=35.193.81.220

# you can get them from the google console web ui > container engine > cluster > show credentials
# GKE_PASSWORD=
# GKE_USERNAME=admin

set -e

if [ "${TRAVIS_BRANCH}" != "master" ]; then
    echo "script only does deployment to production from master"
    exit 0
fi

# http://thylong.com/ci/2016/deploying-from-travis-to-gce/

if [ ! -d "$HOME/google-cloud-sdk/bin" ]; then
    rm -rf $HOME/google-cloud-sdk
    curl https://sdk.cloud.google.com | bash
fi

# Add gcloud to $PATH
source /home/travis/google-cloud-sdk/path.bash.inc
gcloud version
gcloud --quiet components update kubectl

# Auth flow
echo $GCLOUD_KEY | base64 --decode > gcloud.json
gcloud auth activate-service-account $GCLOUD_EMAIL --key-file gcloud.json
ssh-keygen -f ~/.ssh/google_compute_engine -N ""

bin/k8s_deploy.sh
