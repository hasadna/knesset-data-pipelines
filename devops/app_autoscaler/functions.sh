
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
    git clone "${URL}" /repo > /dev/null 2>&1
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
            MSG="Autoscaler - scaling ${1} --autoscaler"
            if [ "${1}" == "down" ]; then
                MSG+=" --force-update-metabase"
            fi
            git commit -m "${MSG}"
            git push origin "HEAD:${DPP_AUTOSCALER_BRANCH}"
        popd > /dev/null
    fi
    sleep 5
    echo " > Done"
}
