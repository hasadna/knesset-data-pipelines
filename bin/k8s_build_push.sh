#!/usr/bin/env bash

# builds all relevant app images and pushed to the Google private repository
# also updated Helm / K8S configurations to make sure current K8S environment uses those images

# usage examples:
#    'bin/k8s_build_push.sh' - build all images
#    'bin/k8s_build_push.sh --app' - build app image
#    'bin/k8s_build_push.sh --committees' - build committees webapp image
#    'bin/k8s_build_push.sh --db-backup' - build db-backup image
#
# by default it downloads latest master branch, to build from local copy:
#    'BUILD_LOCAL=1 bin/k8s_build_push.sh`

source bin/k8s_connect.sh > /dev/null
source bin/functions.sh

if [ -f VERSION.txt ]; then
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi

if [ "${1}" == "" ]; then
    bin/k8s_build_push.sh --app || exit 1
    bin/k8s_build_push.sh --committees || exit 2
    bin/k8s_build_push.sh --db-backup || exit 3
    bin/k8s_build_push.sh --app-autoscaler || exit 4
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
elif [ "${1}" == "--app-autoscaler" ]; then
    build_push app-autoscaler hasadna knesset-data-pipelines master devops/app_autoscaler || exit 7
    exit 0
fi

exit 7
