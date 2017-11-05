#!/usr/bin/env bash

# force an update for a K8S deployment by setting a label with unix timestamp

source bin/k8s_connect.sh > /dev/null
source bin/functions.sh


if [ "${1}" == "" ]; then
    echo "usage: bin/k8s_force_update.sh <deployment_name>"
    exit 1
else
    if [ "${1}" == "metabase" ]; then
        OLD_POOL=`read_values metabase gkeNodePool 2>/dev/null`
        if [ "${OLD_POOL}" != "" ]; then
            if echo $OLD_POOL | grep '^metabase-'; then
                OLD_POOL_NUM=`echo "${OLD_POOL}" | cut -d"-" -f2 -`
                NEW_POOL_NUM=`expr $OLD_POOL_NUM + 1`
                NEW_POOL="metabase-${NEW_POOL_NUM}"
            else
                NEW_POOL="metabase-1"
            fi
            gcloud container node-pools create "${NEW_POOL}" \
                                               "--cluster=${CLOUDSDK_CONTAINER_CLUSTER}" \
                                               --disk-size=20 \
                                               --machine-type=g1-small \
                                               --num-nodes=1 \
                                               --node-labels=app=metabase \
                                               --quiet
            echo " > Waiting for new node"
            while [ `kubectl get nodes | tee /dev/stderr | grep " Ready " | grep -- "-${NEW_POOL}-" | wc -l` != "1" ]; do
                echo .
                sleep 5
            done
            kubectl scale deployment metabase --replicas=2
            kubectl rollout status deployment "metabase"
            gcloud container node-pools delete "${OLD_POOL}" --quiet
            kubectl scale deployment metabase --replicas=1
            set_values '{"metabase": {"gkeNodePool": "'$NEW_POOL'"}}'
        fi
    else
        kubectl patch deployment "${1}" -p "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"date\":\"`date +'%s'`\"}}}}}" || exit 1
    fi
fi

kubectl rollout status deployment "${1}"
