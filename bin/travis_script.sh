#!/usr/bin/env bash

export AUTODEPLOY_MESSAGE="deployment image update from travis_deploy_script"

if [ "${K8S_ENVIRONMENT}" != "" ] && [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    source "devops/k8s/.env.${K8S_ENVIRONMENT}"
fi

if [ "${TRAVIS_PULL_REQUEST}" != "false" ] || \
   [ "${TRAVIS_BRANCH}" != "${CONTINUOUS_DEPLOYMENT_BRANCH}" ] || \
   echo "${TRAVIS_COMMIT_MESSAGE}" | grep "${AUTODEPLOY_MESSAGE}" > /dev/null || \
   echo "${TRAVIS_COMMIT_MESSAGE}" | grep -- "--no-deploy" > /dev/null ; \
then
    echo " > running tests"
    sudo apt-get update
    sudo apt-get install -y antiword
    pip install tox
    if ! bin/test.sh; then
        echo " > Tests failed!"
        exit 1
    fi
    exit 0
fi

if [ "${DEPLOYMENT_BOT_GITHUB_TOKEN}" == "" ] || [ "${SERVICE_ACCOUNT_B64_JSON_SECRET_KEY}" == "" ]; then
    echo " > following environment variables are required for travis deploy: "
    echo " > (they should be created by provision script and set in travis env)"
    echo " > SERVICE_ACCOUNT_B64_JSON_SECRET_KEY"
    echo " > DEPLOYMENT_BOT_GITHUB_TOKEN"
    exit 0
fi

if [ ! -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    echo " > missing environment file devops/k8s/.env.${K8S_ENVIRONMENT}"
    exit 1
fi

if [ "${TRAVIS_TAG}" != "" ]; then
    echo "${TRAVIS_TAG}" > VERSION.txt
else
    echo "v0.0.0-`date +%Y-%m-%d-%H-%M`" > VERSION.txt
fi

export GIT_CONFIG_USER="${CONTINUOUS_DEPLOYMENT_GIT_USER}"
export GIT_CONFIG_EMAIL="${CONTINUOUS_DEPLOYMENT_GIT_EMAIL}"

echo " > install docker"
bin/install_docker.sh
docker version

echo " > install gcloud"
bin/install_gcloud.sh
gcloud version
source "${HOME}/google-cloud-sdk/path.bash.inc"

echo " > install helm client"
bin/install_helm.sh
helm version --client

export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export BUILD_LOCAL=1

IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-app"
if [ -f "${IID_FILE}" ]; then
    OLD_APP_IID=`cat "${IID_FILE}"`
else
    OLD_APP_IID=""
fi

if ! bin/k8s_continuous_deployment.sh; then
    echo " > Failed continuous deployment"
    exit 1
else
    NEW_APP_IID=`cat "${IID_FILE}"`
    if [ "${OLD_APP_IID}" != "${NEW_APP_IID}" ]; then
        echo " > Committing app image change to GitHub"
        git config user.email "${GIT_CONFIG_EMAIL}"
        git config user.name "${GIT_CONFIG_USER}"
        git diff devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml "${IID_FILE}"
        git add devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml "${IID_FILE}"
        git commit -m "${AUTODEPLOY_MESSAGE}"
        git push "https://${DEPLOYMENT_BOT_GITHUB_TOKEN}@github.com/${TRAVIS_REPO_SLUG}.git" "HEAD:${TRAVIS_BRANCH}"
    fi
    echo " > done"
    exit 0
fi
