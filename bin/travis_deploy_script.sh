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

# create a github machine user (https://developer.github.com/v3/guides/managing-deploy-keys/#machine-users)
# get a personal access token for this user, with public_repo access
# add this bot user as collaborator with write access
# DEPLOYMENT_BOT_GITHUB_TOKEN=

## following travis environment variables are used
# branch - must be master
# TRAVIS_BRANCH=master
# the commit sha - used to tag the docker images
# TRAVIS_COMMIT=

set -e

if [ "${TRAVIS_BRANCH}" != "master" ]; then
    echo "script only does deployment to production from master"
    exit 0
fi

if echo $TRAVIS_COMMIT_MESSAGE | grep "deployment image update: " > /dev/null; then
    echo "skipping automatic deployment image updates"
    exit 0
fi


echo " > install and authenticate with gcloud"  # based on http://thylong.com/ci/2016/deploying-from-travis-to-gce/

if [ ! -d "$HOME/google-cloud-sdk/bin" ]; then
    rm -rf $HOME/google-cloud-sdk
    curl https://sdk.cloud.google.com | bash
fi
source /home/travis/google-cloud-sdk/path.bash.inc
gcloud version
gcloud --quiet components update kubectl
echo $GCLOUD_KEY | base64 --decode > gcloud.json
gcloud auth activate-service-account $GCLOUD_EMAIL --key-file gcloud.json
ssh-keygen -f ~/.ssh/google_compute_engine -N ""


echo " > update pipelines app image and commit to git"

bin/k8s_update_deployment_image.py "app" "gcr.io/hasadna-oknesset/knesset-data-pipelines:${TRAVIS_COMMIT}"
git config user.email ori+oknesset-deployment-bot@uumpa.com
git config user.name oknesset-deployment-bot
git add "devops/k8s/app.yaml"
git commit -m "deployment image update: app=gcr.io/hasadna-oknesset/knesset-data-pipelines:${TRAVIS_COMMIT}"
git push "https://${DEPLOYMENT_BOT_GITHUB_TOKEN}@github.com/hasadna/knesset-data-pipelines.git" master


echo " > deploy"

bin/k8s_deploy.sh
