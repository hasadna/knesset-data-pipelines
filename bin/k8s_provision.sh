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

create_service_account() {
    local SERVICE_ACCOUNT_NAME="${1}"
    local SECRET_TEMPDIR="${2}"
    local SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"
    if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_ID}" >&2; then
        echo " > Creating service account ${SERVICE_ACCOUNT_ID}" >&2
        gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" >&2 || exit 1
    else
        echo " > Service account ${SERVICE_ACCOUNT_ID} already exists" >&2
    fi
    gcloud iam service-accounts keys create "--iam-account=${SERVICE_ACCOUNT_ID}" "${SECRET_TEMPDIR}/key" >&2 || exit 1
    echo "${SERVICE_ACCOUNT_ID}"
    exit 0
}

add_service_account_role() {
    local SERVICE_ACCOUNT_ID="${1}"
    local ROLE="${2}"
    gcloud projects add-iam-policy-binding --role "${ROLE}" "${CLOUDSDK_CORE_PROJECT}" --member "serviceAccount:${SERVICE_ACCOUNT_ID}" || exit 1
    exit 0
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
        travis login || exit 1
    fi
    travis env --repo "${TRAVIS_REPO}" --private --org set "${KEY}" "${VALUE}" || exit 1
    exit 0
}

export WHAT="${1}"
export ACTION="${2:---provision}"

mkdir -p "devops/k8s/provision-values-${K8S_ENVIRONMENT}/"

echo " > Provisioning ${WHAT} resources for ${K8S_ENVIRONMENT} environment"

if [ "${WHAT}" == "db" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "db" && exit 0
elif [ "${WHAT}" == "app" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "app" && exit 0
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "cluster" ]; then
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
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "dpp-workers" ]; then
    # TODO: ensure there are enough compute resources for these workers and assign dpp to appropriate node
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/dpp-workers.yaml"
    CPU_REQUESTS=`expr "${DPP_WORKERS:-1}" '*' 0.2`
    MEMORY_REQUESTS="500Mi"
    echo "app:" > $VALUES_FILE
    echo "  dppWorkerConcurrency: \"${DPP_WORKERS:-1}\"" >> $VALUES_FILE
    echo "  cpuRequests: ${CPU_REQUESTS}" >> $VALUES_FILE
    echo "  memoryRequests: \"${MEMORY_REQUESTS}\"" >> $VALUES_FILE
    exit 0
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "metabase" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/metabase.yaml"
    echo "metabase:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableMetabase: true" >> $VALUES_FILE
    exit 0
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "grafana" ]; then
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
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "shared-host" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/shared-host.yaml"
    export SHARED_HOST_NAME=`kubectl get pod -l app=app -o json | jq -r '.items[0].spec.nodeName'`
    echo " > using "${SHARED_HOST_NAME}" as the shared host"
    gcloud compute ssh "${SHARED_HOST_NAME}" \
        --command "sudo mkdir -p /var/shared-host-path/{nginx-html,letsencrypt-etc,letsencrypt-log,app-data} && sudo chown -R root:root /var/shared-host-path"
    echo "global:" > $VALUES_FILE
    echo "  sharedHostName: ${SHARED_HOST_NAME}" >> $VALUES_FILE
    exit 0
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "nginx" ]; then
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
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "letsencrypt" ]; then
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
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "committees" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/committees.yaml"
    echo "committees:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableCommittees: true" >> $VALUES_FILE
    exit 0
elif [ "${ACTION}" == "--provision" ] && [ "${WHAT}" == "continuous-deployment" ]; then
    if [ "${K8S_ENVIRONMENT}" != "production" ]; then
        echo " > Continuous deployment is only supported on production"
        exit 1
    fi
    export SERVICE_ACCOUNT_NAME="kdp-${K8S_ENVIRONMENT}-deployment"
    export SECRET_TEMPDIR="${SECRET_TEMPDIR:-`mktemp -d`}"
    export SERVICE_ACCOUNT_ID="`create_service_account "${SERVICE_ACCOUNT_NAME}" "${SECRET_TEMPDIR}"`"
    export SECRET_KEYFILE="${SECRET_TEMPDIR}/key"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/container.clusterAdmin"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/container.developer"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/storage.admin"
    travis_set_env "hasadna/knesset-data-pipelines" "SERVICE_ACCOUNT_B64_JSON_SECRET_KEY" "`cat "${SECRET_TEMPDIR}/key" | base64 -w0`"
    rm -rf "${SECRET_TEMPDIR}"
    echo
    if ! travis env --repo hasadna/knesset-data-pipelines list | grep 'DEPLOYMENT_BOT_GITHUB_TOKEN='; then
        echo
        echo " > ERROR!"
        echo
        echo " > you need to create a github machine user (https://developer.github.com/v3/guides/managing-deploy-keys/#machine-users)"
        echo " > get a personal access token for this user, with public_repo access"
        echo " > add this bot user as collaborator with write access"
        echo " > you can add a collaborator from the api:"
        echo " > curl -u YourGithubUserName https://api.github.com/repos/hasadna/knesset-data-pipelines/collaborators/oknesset-deployment-bot -X PUT"
        echo
        echo " > Then, set the token in travis:"
        echo ' > travis env --repo hasadna/knesset-data-pipelines --private --org set "DEPLOYMENT_BOT_GITHUB_TOKEN" ""'
        exit 1
    fi
    exit 0
fi

echo " > ERROR! couldn't handle ${WHAT} ${ACTION}"
exit 2
