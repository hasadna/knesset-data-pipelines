#!/usr/bin/env bash

# builds all relevant app images and pushed to the Google private repository
# also updated Helm / K8S configurations to make sure current K8S environment uses those images

# usage examples:
#    'bin/k8s_build_push.sh' - build all images
#    'bin/k8s_build_push.sh --app' - build app image (alos used for flower)
#    'bin/k8s_build_push.sh --committees' - build committees webapp image
#    'bin/k8s_build_push.sh --db-backup' - build db-backup image
#
# by default it downloads latest master branch, to build from local copy:
#    'BUILD_LOCAL=1 bin/k8s_build_push.sh`

source bin/k8s_connect.sh

if [ -f VERSION.txt ]; then
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi

build_push() {
    # build_push <app_name> <github_user> <github_repo> <github_branch_name=master> <build_dir>
    APP_NAME="${1}"
    if [ "${BUILD_LOCAL}" == "1" ] && [ "${1}" == "committees" ] && [ ! -f "../knesset-data-committees-webapp/Dockerfile" ]; then
        echo
        echo " > WARNING!"
        echo
        echo " > cannot build committees webapp locally, will build from remote repo."
        echo
        echo " > This repo is expected to be in ../knesset-data-committees-webapp/"
        echo " > You can run this snippet to clone it:"
        echo " > git clone git@github.com:OriHoch/knesset-data-committees-webapp.git ../knesset-data-committees-webapp/"
        echo
        BUILD_LOCAL=""
    fi
    if [ "${BUILD_LOCAL}" == "1" ] && [ "${3}" == "knesset-data-pipelines" ]; then
        GITHUB_USER=""
        GITHUB_REPO=""
        BRANCH_NAME=""
    else
        GITHUB_USER="${2}"
        GITHUB_REPO="${3}"
        BRANCH_NAME="${4}"
    fi
    BUILD_DIR="${5}"

    SOURCE_CODE_URL="https://codeload.github.com/${GITHUB_USER}/${GITHUB_REPO}/zip/${BRANCH_NAME}"
    DOCKER_TAG="gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-${APP_NAME}:${VERSION}"
    IMAGE_VALUES_FILE="devops/k8s/values-${K8S_ENVIRONMENT}-image-${APP_NAME}.yaml"


    if [ "${GITHUB_REPO}" == "" ]; then
        echo " > building from local directory ${BUILD_DIR}"
        gcloud docker -- build -t "${DOCKER_TAG}" "${BUILD_DIR}"
    else
        echo " > downloading source code from ${SOURCE_CODE_URL}"
        TEMPDIR=`mktemp -d`
        pushd $TEMPDIR
        curl "${SOURCE_CODE_URL}" > source.zip
        unzip source.zip
        rm source.zip
        popd
        pushd "${TEMPDIR}/${GITHUB_REPO}-master"
        echo " > building directory ${TEMPDIR}/${BUILD_DIR}"
        gcloud docker -- build -t "${DOCKER_TAG}" "${BUILD_DIR}"
        popd
        rm -rf $TEMPDIR
    fi

    echo " > pushing tag ${DOCKER_TAG}"
    gcloud docker -- push "${DOCKER_TAG}"

    echo " > generating values file ${IMAGE_VALUES_FILE}"
    echo " > image: \"${DOCKER_TAG}\""
    if [ "${APP_NAME}" == "db-backup" ]; then
        echo "db:" > "${IMAGE_VALUES_FILE}"
        echo "  dbBackupImage: \"${DOCKER_TAG}\"" >> "${IMAGE_VALUES_FILE}"
    else
        echo "${APP_NAME}:" > "${IMAGE_VALUES_FILE}"
        echo "  image: \"${DOCKER_TAG}\"" >> "${IMAGE_VALUES_FILE}"
    fi
    echo >> "${IMAGE_VALUES_FILE}"
    if [ "${APP_NAME}" == "app" ]; then
        echo " > setting flower image (uses same build and values file as app)"
        echo "flower:" >> "${IMAGE_VALUES_FILE}"
        echo "  image: \"${DOCKER_TAG}\"" >> "${IMAGE_VALUES_FILE}"
        echo >> "${IMAGE_VALUES_FILE}"
    fi
}

if [ "${1}" == "" ]; then
    bin/k8s_build_push.sh --app
    bin/k8s_build_push.sh --committees
    bin/k8s_build_push.sh --db-backup
elif [ "${1}" == "--app" ]; then
    build_push app hasadna knesset-data-pipelines master .
elif [ "${1}" == "--committees" ]; then
    build_push committees OriHoch knesset-data-committees-webapp master .
elif [ "${1}" == "--db-backup" ]; then
    build_push db-backup hasadna knesset-data-pipelines master devops/db_backup
fi
