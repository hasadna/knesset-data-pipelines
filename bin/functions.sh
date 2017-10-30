
set_values() {
    bin/update_yaml.py "${1}" "devops/k8s/values-${K8S_ENVIRONMENT}-provision.yaml"
}

create_disk() {
    local DISK_SIZE="${1}"
    local APP="${2}"
    echo " > Provisioning ${1} persistent disk knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    gcloud compute disks create --size "${DISK_SIZE}" "knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
}

provision_disk() {
    local DISK_SIZE="${1}"
    local APP="${2}"
    create_disk "${DISK_SIZE}" "${APP}"
    echo " > Updating persistent disk name in values file"
    set_values '{"'$APP'": {"gcePersistentDiskName": "knesset-data-pipelines-'$K8S_ENVIRONMENT'-'$APP'"}}'
    exit 0
}

delete_disk() {
    local APP="${1}"
    echo " > Deleting persistent disk knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    gcloud compute disks delete "knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    rm "devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
    set_values '{"'$APP'": {"gcePersistentDiskName": null}}'
    exit 0
}

handle_disk_provisioning() {
    local ACTION="${1}"
    local DISK_SIZE="${2}"
    local APP="${3}"
    if [ "${ACTION}" == "--provision" ]; then
        provision_disk "${DISK_SIZE}" "${APP}" && exit 0
    elif [ "${ACTION}" == "--delete" ]; then
        delete_disk "${APP}" && exit 0
    elif [ "${ACTION}" == "--list" ]; then
        gcloud compute disks list && exit 0
    fi

}

create_service_account() {
    local SERVICE_ACCOUNT_NAME="${1}"
    local SECRET_TEMPDIR="${2}"
    local SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"
    if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_ID}" >&2; then
        echo " > Creating service account ${SERVICE_ACCOUNT_ID}" >&2
        if ! gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" >&2; then
            echo "> Failed to create service account" >&2
        fi
    else
        echo " > Service account ${SERVICE_ACCOUNT_ID} already exists" >&2
    fi
    echo " > Deleting all keys from service account" >&2
    for KEY in `gcloud iam service-accounts keys list "--iam-account=${SERVICE_ACCOUNT_ID}" 2>/dev/null | tail -n+2 | cut -d" " -f1 -`; do
        gcloud iam service-accounts keys --quiet delete "${KEY}" "--iam-account=${SERVICE_ACCOUNT_ID}" > /dev/null 2>&1
    done
    if ! gcloud iam service-accounts keys create "--iam-account=${SERVICE_ACCOUNT_ID}" "${SECRET_TEMPDIR}/key" >&2; then
        echo " > Failed to create account key" >&2
    fi
    echo "${SERVICE_ACCOUNT_ID}"
    echo " > Created service account ${SERVICE_ACCOUNT_ID}" >&2
}

add_service_account_role() {
    local SERVICE_ACCOUNT_ID="${1}"
    local ROLE="${2}"
    if ! gcloud projects add-iam-policy-binding --role "${ROLE}" "${CLOUDSDK_CORE_PROJECT}" --member "serviceAccount:${SERVICE_ACCOUNT_ID}" >/dev/null; then
        echo " > Failed to add iam policy binding"
    fi
    echo " > Added service account role ${ROLE}"
}

travis_set_env() {
    local TRAVIS_REPO="${1}"
    local KEY="${2}"
    local VALUE="${3}"
    if ! which travis > /dev/null; then
        echo " > Trying to install travis"
        sudo apt-get install ruby ruby-dev
        sudo gem install travis
    fi
    if ! travis whoami; then
        echo " > Login to Travis using GitHub credentials which have write permissions on ${TRAVIS_REPO}"
        travis login
    fi
    travis env --repo "${TRAVIS_REPO}" --private --org set "${KEY}" "${VALUE}"
}

env_config_getset() {
    local CURRENT_VALUE="${1}"
    local PROMPT="${2}"
    local VAR_NAME="${3}"
    if [ "${CURRENT_VALUE}" == "" ]; then
        read -p "${PROMPT}: "
        echo "export ${VAR_NAME}=\"${REPLY}\"" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo "${REPLY}"
    else
        echo "${CURRENT_VALUE}"
    fi
}

env_config_set() {
    local CURRENT_VALUE="${1}"
    local VAR_NAME="${2}"
    local VALUE="${3}"
    if [ "${CURRENT_VALUE}" == "" ]; then
        echo "export ${VAR_NAME}=\"${VALUE}\"" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo "${VALUE}"
    else
        echo "${CURRENT_VALUE}"
    fi
}

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
    IID_FILE="devops/k8s/iidfile-${K8S_ENVIRONMENT}-${APP_NAME}"
    if [ -f "${IID_FILE}" ]; then
        OLD_IID=`cat "${IID_FILE}"`
    else
        OLD_IID=""
    fi
    if [ "${GITHUB_REPO}" == "" ]; then
        echo " > building from local directory ${BUILD_DIR}"
        gcloud docker -- build `[ "${DEBUG}" != "1" ] && echo "-q"` -t "${DOCKER_TAG}" --iidfile "${IID_FILE}" "${BUILD_DIR}" || exit 1
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
    if  [ "${OLD_IID}" != "${NEW_IID}" ]; then
        echo " > pushing tag ${DOCKER_TAG}"
        gcloud docker -- push "${DOCKER_TAG}" || exit 3
        echo " > saving values"
        echo " > image: \"${DOCKER_TAG}\""
        if [ "${APP_NAME}" == "db-backup" ]; then
            set_values '{"db": {"dbBackupImage": "'$IMAGE_VALUES_FILE'"}}'
            set_values '{"jobs": {"restoreDbImage": "'$IMAGE_VALUES_FILE'"}}'
        elif [ "${APP_NAME}" == "app-autoscaler" ]; then
            set_values '{"app": {"autoscalerImage": "'$IMAGE_VALUES_FILE'"}}'
        else
            set_values '{"'$APP_NAME'": {"image": "'$IMAGE_VALUES_FILE'"}}'
        fi
    else
        echo " > skipping values file update"
    fi
}