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
    if ! curl "${DPP_PIPELINES_URL}/api/raw/status" > /dpp-status.json 2> /dev/null; then
        exit 1
    fi
    if ! cat /dpp-status.json | jq '.[].dirty' > /dpp-status-dirty.json; then
        exit 2
    fi
    if ! cat /dpp-status.json | jq '.[].state' > /dpp-status-state.json; then
        exit 3
    fi
    NUM_DIRTY=`cat /dpp-status-dirty.json | grep true | wc -l`
    NUM_FAILED=`cat /dpp-status-state.json | grep '"FAILED"' | wc -l`
    NUM_RUNNING=`cat /dpp-status-state.json | grep '"RUNNING"' | wc -l`
    if [ "${NUM_DIRTY}" == "" ] || [ "${NUM_FAILED}" == "" ] || [ "${NUM_RUNNING}" == "" ]; then
        exit 4
    fi
    update_repo > /dev/null
    SCALED_UP=`is_scaled_up`
    if [ "${SCALED_UP}" == "" ]; then
        exit 5
    fi
    HOUR=`date +%H`
    echo "SCALED_UP=${SCALED_UP}, HOUR=${HOUR}, NUM_DIRTY=${NUM_DIRTY}, NUM_FAILED=${NUM_FAILED}, NUM_RUNNING=${NUM_RUNNING}"
    if [ "${SCALED_UP}" == "0" ]; then
        if [ "${NUM_DIRTY}" -gt "${NUM_FAILED}" ]; then
            date
            echo " > got some dirty nodes which are not due to failure - scaling up to handle them"
            scale up
        elif [ "${HOUR}" == "00" ]; then
            date
            echo " > scheduled scale up at midnight"
            scale up
        fi
    elif [ "${SCALED_UP}" == "1" ] &&\
         [ "${NUM_DIRTY}" -le "${NUM_FAILED}" ] &&\
         [ "${NUM_RUNNING}" -eq "0" ] &&\
         [ "${HOUR}" != "00" ] && [ "${HOUR}" != "01" ] && [ "${HOUR}" != "02" ]
    then
        date
        echo " > scaling down"
        scale down
    fi
done
