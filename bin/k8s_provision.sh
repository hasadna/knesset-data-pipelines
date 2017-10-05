#!/usr/bin/env bash

# provision resources required by the cluster and create values files under devops/k8s/provision-values-${K8S_ENVIRONMENT}/

if [ "${1}" == "" ]; then
    echo "usage: bin/k8s_provision.sh <WHAT> [--list|--delete]"
    exit 1
fi

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
    echo " > Updating persistent disk name in values file devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
    echo "${APP}:" > "devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
    echo "  gcePersistentDiskName: \"knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}\"" >> "devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
    exit 0
}

delete_disk() {
    local APP="${1}"
    echo " > Deleting persistent disk knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    gcloud compute disks delete "knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    rm "devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
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

export WHAT="${1}"
export ACTION="${2:---provision}"

mkdir -p "devops/k8s/provision-values-${K8S_ENVIRONMENT}/"

echo " > Provisioning ${WHAT} resources for ${K8S_ENVIRONMENT} environment"

if [ "${WHAT}" == "db" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "db" && exit 0
elif [ "${WHAT}" == "app" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "app" && exit 0
elif [ "${WHAT}" == "cluster" ]; then
    if [ "${ACTION}" == "--provision" ]; then
        gcloud container clusters create "knesset-data-pipelines-${K8S_ENVIRONMENT}" \
            --disk-size=20 \
            --machine-type=g1-small \
            --num-nodes=3
        while ! gcloud container clusters get-credentials "knesset-data-pipelines-${K8S_ENVIRONMENT}"; do
            echo " failed to get credentials to the clusters.. sleeping 5 seconds and retrying"
            sleep 5
        done
        echo "kubectl config use-context `kubectl config current-context`" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        exit 0
    fi
elif [ "${WHAT}" == "db-restore" ] || [ "${WHAT}" == "db-backup" ]; then
    export SERVICE_ACCOUNT_NAME="kdp-${K8S_ENVIRONMENT}-db-backups"
    export STORAGE_BUCKET_NAME="kdp-${K8S_ENVIRONMENT}-db-backups"
    export SECRET_NAME=db-backup-upload-google-key
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/${WHAT}.yaml"
    if [ "${ACTION}" == "--provision" ]; then
        if [ "${WHAT}" == "db-restore" ] && [ "${GS_URL}" == "" ]; then
            echo " > must set GS_URL environment variable to restore"
            exit 1
        fi
        source <(devops/db_backup/provision_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}")
        kubectl delete secret "${SECRET_NAME}"
        kubectl create secret generic "${SECRET_NAME}" --from-file "${SECRET_KEY_FILE}"
        rm -rf "${SECRET_TEMPDIR}"
        if [ "${WHAT}" == "db-restore" ]; then
            echo "jobs:" > $VALUES_FILE
            echo "  restoreDbJobName: db-restore-`date +%y-%m-%d-%H-%M`" >> $VALUES_FILE
            echo "  restoreDbGsUrl: ${GS_URL}" >> $VALUES_FILE
            echo "  restoreDbServiceAccountId: ${SERVICE_ACCOUNT_ID}" >> $VALUES_FILE
            echo "  restoreDbProjectId: ${CLOUDSDK_CORE_PROJECT}" >> $VALUES_FILE
            echo "  restoreDbZone: ${CLOUDSDK_COMPUTE_ZONE}" >> $VALUES_FILE
            echo "  restoreDbServiceAccountKeySecret: ${SECRET_NAME}" >> $VALUES_FILE
        else
            echo "db:" > $VALUES_FILE
            echo "  backupUploadProjectId: ${CLOUDSDK_CORE_PROJECT}" >> $VALUES_FILE
            echo "  backupUploadZone: us-central1-a" >> $VALUES_FILE
            echo "  backupUploadServiceAccountId: ${SERVICE_ACCOUNT_ID}" >> $VALUES_FILE
            echo "  backupUploadServiceAccountKeySecret: ${SECRET_NAME}" >> $VALUES_FILE
            echo "  backupUploadBucketName: ${STORAGE_BUCKET_NAME}" >> $VALUES_FILE
        fi
        exit 0
    elif [ "${ACTION}" == "--delete" ]; then
        devops/db_backup/cleanup_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}"
        exit 0
    fi
elif [ "${WHAT}" == "dpp-workers" ]; then
    # TODO: ensure there are enough compute resources for these workers and assign dpp to appropriate node
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/dpp-workers.yaml"
    CPU_REQUESTS=`expr "${DPP_WORKERS:-1}" '*' 0.2`
    MEMORY_REQUESTS="500Mi"
    echo "app:" > $VALUES_FILE
    echo "  dppWorkerConcurrency: \"${DPP_WORKERS:-1}\"" >> $VALUES_FILE
    echo "  cpuRequests: ${CPU_REQUESTS}" >> $VALUES_FILE
    echo "  memoryRequests: \"${MEMORY_REQUESTS}\"" >> $VALUES_FILE
    exit 0
elif [ "${WHAT}" == "metabase" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/metabase.yaml"
    echo "metabase:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableMetabase: true" >> $VALUES_FILE
    exit 0
elif [ "${WHAT}" == "grafana" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/grafana.yaml"
    create_disk "${DISK_SIZE:-5GB}" "influxdb"
    echo "app:" > $VALUES_FILE
    echo "  influxDb: dpp" >> $VALUES_FILE
    echo "influxdb:" >> $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "  gcePersistentDiskName: \"knesset-data-pipelines-${K8S_ENVIRONMENT}-influxdb\"" >> $VALUES_FILE
    echo "grafana:" >> $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableGrafana: true" >> $VALUES_FILE
    exit 0
elif [ "${WHAT}" == "shared-host" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/shared-host.yaml"
    export SHARED_HOST_NAME=`kubectl get pod -l app=app -o json | jq -r '.items[0].spec.nodeName'`
    echo " > using "${SHARED_HOST_NAME}" as the shared host"
    gcloud compute ssh "${SHARED_HOST_NAME}" \
        --command "sudo mkdir -p /var/shared-host-path/{nginx-html,letsencrypt-etc,letsencrypt-log,app-data} && sudo chown -R root:root /var/shared-host-path"
    echo "global:" > $VALUES_FILE
    echo "  sharedHostName: ${SHARED_HOST_NAME}" >> $VALUES_FILE
    exit 0
elif [ "${WHAT}" == "nginx" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/nginx.yaml"
    echo "nginx:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "  enableData: true" >> $VALUES_FILE
    echo "  enablePipelines: true" >> $VALUES_FILE
    echo "  enableFlower: true" >> $VALUES_FILE
    echo "  enableAdminer: true" >> $VALUES_FILE
    echo " > creating htpasswd for user 'superadmin'"
    export USERNAME=superadmin
    export TEMPDIR=`mktemp -d`
    which htpasswd > /dev/null || sudo apt-get install apache2-utils
    htpasswd -c "${TEMPDIR}/htpasswd" $USERNAME
    kubectl delete secret nginx-htpasswd
    kubectl create secret generic nginx-htpasswd --from-file "${TEMPDIR}/"
    rm -rf $TEMPDIR
    echo "  htpasswdSecretName: nginx-htpasswd" >> $VALUES_FILE
    echo "flower:" >> $VALUES_FILE
    echo "  urlPrefix: flower" >> $VALUES_FILE
    echo " > upgrading helm, and waiting for nginx service to get the load balancer iP"
    bin/k8s_helm_upgrade.sh
    while [ `kubectl get service nginx -o json  | jq -r '.status.loadBalancer.ingress[0].ip'` == "null" ]; do
        sleep 1
    done
    export NGINX_HOST_IP=`kubectl get service nginx -o json  | jq -r '.status.loadBalancer.ingress[0].ip'`
    echo " > NGINX_HOST_IP=${NGINX_HOST_IP}"
    echo "global:" >> $VALUES_FILE
    echo "  rootUrl: http://${NGINX_HOST_IP}" >> $VALUES_FILE
    exit 0
elif [ "${WHAT}" == "letsencrypt" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/letsencrypt.yaml"
    echo "letsencrypt:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo " > Provisions to use SSL_DOMAIN ${SSL_DOMAIN}"
    if [ "${SSL_DOMAIN}" != "" ]; then
        echo "nginx:" >> $VALUES_FILE
        echo "  sslDomain: ${SSL_DOMAIN}" >> $VALUES_FILE
        echo "global:" >> $VALUES_FILE
        echo "  rootUrl: https://${SSL_DOMAIN}" >> $VALUES_FILE
    fi
    exit 0
elif [ "${WHAT}" == "committees" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/committees.yaml"
    echo "committees:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableCommittees: true" >> $VALUES_FILE
    exit 0
fi

echo " > ERROR! couldn't handle ${WHAT} ${ACTION}"
exit 2
