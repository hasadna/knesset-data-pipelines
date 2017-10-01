#!/usr/bin/env bash

source bin/k8s_connect.sh

if [ -f VERSION.txt ]; then
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi

build_push() {
    TEMPDIR=`mktemp -d`
    pushd $TEMPDIR >&2
    curl https://codeload.github.com/hasadna/knesset-data-pipelines/zip/master > source.zip
    unzip source.zip  >&2
    rm source.zip  >&2
    popd  >&2
    pushd $TEMPDIR/knesset-data-pipelines-master  >&2
    gcloud docker -- build -t "gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-${1}:${VERSION}" .  >&2
    gcloud docker -- push "gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-${1}:${VERSION}"  >&2
    popd  >&2
    rm -rf $TEMPDIR  >&2
    echo "gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-${1}:${VERSION}"
}

APP_IMAGE=`build_push app`
echo "app:" > "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"
echo "  image: \"${APP_IMAGE}\"" >> "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"
echo >> "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"
echo "flower:" >> "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"
echo "  image: \"${APP_IMAGE}\"" >> "devops/k8s/values-${K8S_ENVIRONMENT}-images.yaml"

echo " > updated images"
echo " > APP_IMAGE=${APP_IMAGE}"
