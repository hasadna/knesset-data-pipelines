
get_num_dirty_pipelines() {
    if ! curl "${DPP_PIPELINES_URL}/api/raw/status" > /dpp-status.json 2> /dev/null; then
        exit 1
    fi
    if ! cat /dpp-status.json | jq '.[].dirty' > /dpp-status-dirty.json; then
        exit 2
    fi
    cat /dpp-status-dirty.json | grep true | wc -l
}

get_num_failed_pipelines() {
    if ! curl "${DPP_PIPELINES_URL}/api/raw/status" > /dpp-status.json 2> /dev/null; then
        exit 1
    fi
    if ! cat /dpp-status.json | jq '.[].state' > /dpp-status-state.json; then
        exit 2
    fi
    cat /dpp-status-state.json | grep '"FAILED"' | wc -l
}

is_scaled_up() {
    if [ `/read_yaml.py "/repo/${DPP_PROVISION_VALUES_FILE}" app enableWorkers` == "True" ]; then
        echo "1"
    else
        echo "0"
    fi
}

clone_repo() {
    URL="https://${DPP_AUTOSCALER_TOKEN}@github.com/${DPP_AUTOSCALER_REPO}.git"
    rm -rf /repo
    git clone "${URL}" /repo
}

update_repo() {
    pushd /repo > /dev/null
    git pull origin "${DPP_AUTOSCALER_BRANCH}"
    popd > /dev/null
}

scale() {
    echo " > Scaling ${1}"
    sleep 5
    SET_VALUES=""
    if [ "${1}" == "up" ]; then
        SET_VALUES='{
            "app": {
                "dppWorkerConcurrency": 4,
                "dppWorkerReplicas": 2,
                "cpuRequests": 0.7,
                "memoryRequests": "1800Mi",
                "enableWorkers": true
            }
        }'
    else
        SET_VALUES='{
            "app": {
                "enableWorkers": false
            }
        }'
    fi
    if [ "${SET_VALUES}" != "" ]; then
        echo " > updating provision values and committing"
        /update_yaml.py "${SET_VALUES}" "/repo/${DPP_PROVISION_VALUES_FILE}"
        pushd /repo > /dev/null
            git config user.email "${DPP_AUTOSCALER_EMAIL}"
            git config user.name "${DPP_AUTOSCALER_USER}"
            git diff ${DPP_PROVISION_VALUES_FILE}
            git add ${DPP_PROVISION_VALUES_FILE}
            git commit -m "Autoscaler - scaling ${1}"
            git push origin "HEAD:${DPP_AUTOSCALER_BRANCH}"
        popd > /dev/null
    fi
    sleep 5
    echo " > Done"
}
