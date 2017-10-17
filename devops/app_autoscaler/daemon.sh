#!/usr/bin/env bash

# daemon that monitors the pipelines statuses and updates provision values in github to scale up / down


if [ "${DPP_AUTOSCALER_REPO}" == "" ] || [ "${DPP_AUTOSCALER_USER}" == "" ] || [ "${DPP_AUTOSCALER_EMAIL}" == "" ] \
    || [ "${DPP_AUTOSCALER_BRANCH}" == "" ] || [ "${DPP_AUTOSCALER_TOKEN}" == "" ] || [ "${DPP_PROVISION_VALUES_FILE}" == "" ]; then
    echo " > Missing git related environment variables"
    exit 1
fi

if [ "${DPP_AUTOSCALER_INTERVAL}" == "" ] || [ "${DPP_PIPELINES_URL}" == "" ]; then
    echo " > Missing autoscaler environment variables"
    exit 3
fi

source /functions.sh

clone_repo

sleep 5

while true; do
    sleep "${DPP_AUTOSCALER_INTERVAL}"
    NUM_DIRTY=`get_num_dirty_pipelines`
    NUM_FAILED=`get_num_failed_pipelines`
    if [ "${NUM_DIRTY}" == "" ] || [ "${NUM_FAILED}" == "" ]; then
        exit 4
    fi
    update_repo > /dev/null
    SCALED_UP=`is_scaled_up`
    if [ "${SCALED_UP}" == "" ]; then
        exit 5
    fi
    echo "NUM_DIRTY=${NUM_DIRTY}, NUM_FAILED=${NUM_FAILED}, SCALED_UP=${SCALED_UP}"
    if [ "${NUM_DIRTY}" -gt "${NUM_FAILED}" ] && [ "${SCALED_UP}" == "0" ]; then
        date
        echo " > got some dirty nodes which are not due to failure - scaling up to handle them"
        scale up
    elif [ "${NUM_DIRTY}" -le "${NUM_FAILED}" ] && [ "${SCALED_UP}" == "1" ]; then
        date
        echo " > no more dirty nodes (which are not failures) - scaling down"
        scale down
    fi
done
