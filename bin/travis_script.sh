#!/usr/bin/env bash

if [ "${K8S_ENVIRONMENT}" != "" ] && [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
    source "devops/k8s/.env.${K8S_ENVIRONMENT}"
fi

if [ "${TRAVIS_PULL_REQUEST}" != "false" ] || \
   [ "${TRAVIS_BRANCH}" != "${CONTINUOUS_DEPLOYMENT_BRANCH}" ] || \
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

pip install pyyaml

export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export BUILD_LOCAL=1

IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-app"
if [ -f "${IID_FILE}" ]; then
    OLD_APP_IID=`cat "${IID_FILE}"`
else
    OLD_APP_IID=""
fi

if echo "${TRAVIS_COMMIT_MESSAGE}" | grep -- "--autoscaler" > /dev/null; then
    export K8S_CD_AUTOSCALER="1"
else
    export K8S_CD_AUTOSCALER="0"
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
        git diff "devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml" "${IID_FILE}"
        git add "devops/k8s/values-${K8S_ENVIRONMENT}-image-app.yaml" "${IID_FILE}"
        MSG="deployment image update from travis_deploy_script --no-deploy"
        MANAGE_VALUES_FILE="devops/k8s/values-${K8S_ENVIRONMENT}-image-app-manage.yaml"
        if git diff --exit-code "${MANAGE_VALUES_FILE}"; then
            if git add "${MANAGE_VALUES_FILE}"; then
                echo " > updated app manage image values file"
                MSG+=" (updated management image)"
            fi
        fi
        SERVE_VALUES_FILE="devops/k8s/values-${K8S_ENVIRONMENT}-image-app-serve.yaml"
        if git diff --exit-code "${SERVE_VALUES_FILE}"; then
            if git add "${SERVE_VALUES_FILE}"; then
                echo " > updated app serve image values file"
                MSG+=" (updated serve image)"
            fi
        fi
        git commit -m "${MSG}"
        git push "https://${DEPLOYMENT_BOT_GITHUB_TOKEN}@github.com/${TRAVIS_REPO_SLUG}.git" "HEAD:${TRAVIS_BRANCH}"
    fi
    echo " > done"
    exit 0
fi
