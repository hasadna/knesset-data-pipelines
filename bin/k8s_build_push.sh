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

source bin/k8s_connect.sh > /dev/null

if [ -f VERSION.txt ]; then
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi

build_push() {
    local APP_NAME="${1}"
    local GITHUB_USER="${2}"
    local GITHUB_REPO="${3}"
    local GITHUB_BRANCH="${4}"
    local BUILD_DIR="${5}"
    if [ "${BUILD_LOCAL}" == "1" ]; then
        if [ "${APP_NAME}" == "committees" ]; then
            if [ -f "../knesset-data-committees-webapp/Dockerfile" ]; then
                # set build dir to local copy of the committees webapp
                local BUILD_DIR="../knesset-data-committees-webapp/"
                # clearing GitHub details - which will cause to build locally
                local GITHUB_USER=""
                local GITHUB_REPO=""
                local GITHUB_BRANCH=""
            else
                echo
                echo " > WARNING!"
                echo
                echo " > cannot build committees webapp locally, will build from remote repo."
                echo
                echo " > This repo is expected to be in ../knesset-data-committees-webapp/"
                echo " > You can run this snippet to clone it:"
                echo " > git clone git@github.com:OriHoch/knesset-data-committees-webapp.git ../knesset-data-committees-webapp/"
                echo
            fi
        else
            # clearing GitHub details - which will cause to build locally
            local GITHUB_USER=""
            local GITHUB_REPO=""
            local GITHUB_BRANCH=""
        fi
    fi
    SOURCE_CODE_URL="https://codeload.github.com/${GITHUB_USER}/${GITHUB_REPO}/zip/${GITHUB_BRANCH}"
    DOCKER_TAG="gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP_NAME}:${VERSION}"
    IMAGE_VALUES_FILE="devops/k8s/values-${K8S_ENVIRONMENT}-image-${APP_NAME}.yaml"
    IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-${APP_NAME}"
    if [ -f "${IID_FILE}" ]; then
        OLD_IID=`cat "${IID_FILE}"`
    else
        OLD_IID=""
    fi
    if [ "${GITHUB_REPO}" == "" ]; then
        echo " > building from local directory ${BUILD_DIR}"
        gcloud docker -- build -q -t "${DOCKER_TAG}" --iidfile "${IID_FILE}" "${BUILD_DIR}" || exit 1
    else
        echo " > downloading source code from ${SOURCE_CODE_URL}"
        TEMPDIR=`mktemp -d`
        pushd $TEMPDIR > /dev/null
        curl -sS "${SOURCE_CODE_URL}" > source.zip
        unzip -q source.zip
        rm source.zip > /dev/null
        popd > /dev/null
        pushd "${TEMPDIR}/${GITHUB_REPO}-master" > /dev/null
        echo " > building directory ${TEMPDIR}/${BUILD_DIR}"
        gcloud docker -- build -q -t "${DOCKER_TAG}" --iidfile ./iidfile "${BUILD_DIR}" || exit 2
        popd > /dev/null
        cp "${TEMPDIR}/${GITHUB_REPO}-master/iidfile" "${IID_FILE}" > /dev/null
        rm -rf $TEMPDIR > /dev/null
    fi
    NEW_IID=`cat "${IID_FILE}"`
    if [ "${OLD_IID}" != "${NEW_IID}" ]; then
        echo " > pushing tag ${DOCKER_TAG}"
        gcloud docker -- push "${DOCKER_TAG}" || exit 3
        echo " > generating values file ${IMAGE_VALUES_FILE}"
        echo " > image: \"${DOCKER_TAG}\""
        if [ "${APP_NAME}" == "db-backup" ]; then
            echo "db:" > "${IMAGE_VALUES_FILE}"
            echo "  dbBackupImage: \"${DOCKER_TAG}\"" >> "${IMAGE_VALUES_FILE}"
            echo >> "${IMAGE_VALUES_FILE}"
            echo "jobs:" >> "${IMAGE_VALUES_FILE}"
            echo "  restoreDbImage: \"${DOCKER_TAG}\"" >> "${IMAGE_VALUES_FILE}"
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
    else
        echo " > iid is unchanged, skipping values file update"
    fi
}

if [ "${1}" == "" ]; then
    bin/k8s_build_push.sh --app || exit 1
    bin/k8s_build_push.sh --committees || exit 2
    bin/k8s_build_push.sh --db-backup || exit 3
    exit 0
elif [ "${1}" == "--app" ]; then
    build_push app hasadna knesset-data-pipelines master . || exit 4
    exit 0
elif [ "${1}" == "--committees" ]; then
    build_push committees OriHoch knesset-data-committees-webapp master . || exit 5
    exit 0
elif [ "${1}" == "--db-backup" ]; then
    build_push db-backup hasadna knesset-data-pipelines master devops/db_backup || exit 6
    exit 0
fi

exit 7
