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

export WHAT="${1}"
if [ "${2}" == "--list" ] || [ "${2}" == "--delete" ]; then
    export ACTION="${2}"
else
    export ACTION="--provision"
fi

if [ "${WHAT}${ACTION}" != "cluster--provision" ]; then
    source bin/k8s_connect.sh > /dev/null
elif [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

mkdir -p "devops/k8s/provision-values-${K8S_ENVIRONMENT}/"

echo " > Provisioning ${WHAT} resources for ${K8S_ENVIRONMENT} environment"

if [ "${WHAT}" == "db" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "db" && exit 0

elif [ "${WHAT}" == "app" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "app" && exit 0

elif [ "${WHAT}" == "minio" ]; then
    handle_disk_provisioning "${ACTION}" "${DISK_SIZE:-5GB}" "minio" && exit 0

elif [ "${WHAT}" == "cluster" ]; then
    if [ "${ACTION}" == "--provision" ]; then
        if [ -f "devops/k8s/.env.${K8S_ENVIRONMENT}" ]; then
            echo " > found existing cluster configuration at devops/k8s/.env.${K8S_ENVIRONMENT}"
            echo " > please delete that file before provisioning a new cluster"
            exit 1
        fi
        if [ ! -f "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" ]; then
            echo " > missing secrets file: devops/k8s/secrets.env.${K8S_ENVIRONMENT}"
            exit 2
        fi
        echo " > Will create a new cluster, this might take a while..."
        echo "You should have a Google project ID with active billing"
        echo "Cluster will comprise of 3 g1-small machines (shared vCPU, 1.70GB ram)"
        echo "We also utilize some other resources which are negligable"
        echo "Total cluster cost shouldn't be more then ~0.09 USD per hour"
        echo "When done, run 'bin/k8s_provision.sh --delete' to ensure cluster is destroyed and billing will stop"
        read -p "Enter your authenticated, billing activated, Google project id: " GCLOUD_PROJECT_ID
        echo " > Creating devops/k8s/.env.${K8S_ENVIRONMENT} file"
        echo "export K8S_ENVIRONMENT=${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo "export CLOUDSDK_CORE_PROJECT=${GCLOUD_PROJECT_ID}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo "export CLOUDSDK_COMPUTE_ZONE=us-central1-a" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo "export CLOUDSDK_CONTAINER_CLUSTER=knesset-data-pipelines-${K8S_ENVIRONMENT}" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        source "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo " > Creating the cluster"
        gcloud container clusters create "knesset-data-pipelines-${K8S_ENVIRONMENT}" \
            --disk-size=20 \
            --machine-type=g1-small \
            --num-nodes=3
        while ! gcloud container clusters get-credentials "knesset-data-pipelines-${K8S_ENVIRONMENT}"; do
            echo " failed to get credentials to the clusters.. sleeping 5 seconds and retrying"
            sleep 5
        done
        echo "kubectl config use-context `kubectl config current-context`" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"
        echo " > Creating persistent disks"
        bin/k8s_provision.sh db
        bin/k8s_provision.sh app
        if [ "${K8S_ENVIRONMENT}" == "production" ]; then
            DISK_SIZE=50GB bin/k8s_provision.sh minio
        else
            bin/k8s_provision.sh minio
        fi
        echo " > sleeping 10 seconds to let cluster initialize some more.."
        bin/k8s_provision.sh helm
        bin/k8s_provision.sh secrets
        echo " > Done, cluster is ready"
        exit 0
    elif [ "${ACTION}" == "--delete" ]; then
        if [ "${K8S_ENVIRONMENT}" != "staging" ]; then
            echo " > cluster cleanup is only supported for staging environment"
            exit 1
        fi
        echo " > deleting cluster (${K8S_ENVIRONMENT} environment)"
        read -p "Are you sure you want to continue? [y/N]: "
        if [ "${REPLY}" == "y" ]; then
            gcloud container clusters delete "${CLOUDSDK_CONTAINER_CLUSTER}"
        fi
        echo " > deleting persistent disks"
        read -p "Are you sure you want to continue? [y/N]: "
        if [ "${REPLY}" == "y" ]; then
            bin/k8s_provision.sh db --delete
            bin/k8s_provision.sh app --delete
        fi
        echo " > deleting devops/k8s/.env.${K8S_ENVIRONMENT}"
        read -p "Are you sure you want to continue? [y/N]: "
        if [ "${REPLY}" == "y" ]; then
            rm "devops/k8s/.env.${K8S_ENVIRONMENT}"
        fi
        echo " > done"
        echo " > Remaining google resources"
        gcloud compute disks list
        echo " > please review google console for any remaining billable services!"
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

elif [ "${ACTION}-${WHAT}" == "--provision-dpp-workers" ]; then
    # TODO: ensure there are enough compute resources for these workers and assign dpp to appropriate node
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/dpp-workers.yaml"
    echo "app:" > $VALUES_FILE
    echo "  dppWorkerConcurrency: 1" >> $VALUES_FILE
    echo "  dppWorkerReplicas: 3" >> $VALUES_FILE
    echo "  cpuRequests: 0.20" >> $VALUES_FILE
    echo "  memoryRequests: \"150Mi\"" >> $VALUES_FILE
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-metabase" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/metabase.yaml"
    echo "metabase:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableMetabase: true" >> $VALUES_FILE
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-grafana" ]; then
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

elif [ "${ACTION}-${WHAT}" == "--provision-shared-host" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/shared-host.yaml"
    export SHARED_HOST_NAME=`kubectl get pod -l app=app -o json | jq -r '.items[0].spec.nodeName'`
    echo " > using "${SHARED_HOST_NAME}" as the shared host"
    gcloud compute ssh "${SHARED_HOST_NAME}" \
        --command "sudo mkdir -p /var/shared-host-path/{nginx-html,letsencrypt-etc,letsencrypt-log,app-data} && sudo chown -R root:root /var/shared-host-path"
    echo "global:" > $VALUES_FILE
    echo "  sharedHostName: ${SHARED_HOST_NAME}" >> $VALUES_FILE
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-nginx" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/nginx.yaml"
    echo "nginx:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
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

elif [ "${ACTION}-${WHAT}" == "--provision-letsencrypt" ]; then
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

elif [ "${ACTION}-${WHAT}" == "--provision-committees" ]; then
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/committees.yaml"
    echo "committees:" > $VALUES_FILE
    echo "  enabled: true" >> $VALUES_FILE
    echo "nginx:" >> $VALUES_FILE
    echo "  enableCommittees: true" >> $VALUES_FILE
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-continuous-deployment" ]; then
    export CONTINUOUS_DEPLOYMENT_REPO=`env_config_getset "${CONTINUOUS_DEPLOYMENT_REPO}" "Github repo" CONTINUOUS_DEPLOYMENT_REPO`
    export CONTINUOUS_DEPLOYMENT_GIT_USER=`env_config_getset "${CONTINUOUS_DEPLOYMENT_GIT_USER}" "Deployer bot user" CONTINUOUS_DEPLOYMENT_GIT_USER`
    export CONTINUOUS_DEPLOYMENT_GIT_EMAIL=`env_config_getset "${CONTINUOUS_DEPLOYMENT_GIT_EMAIL}" "Deployer bot email" CONTINUOUS_DEPLOYMENT_GIT_EMAIL`
    export CONTINUOUS_DEPLOYMENT_BRANCH=`env_config_set "${CONTINUOUS_DEPLOYMENT_BRANCH}" CONTINUOUS_DEPLOYMENT_BRANCH master`
    export SERVICE_ACCOUNT_NAME="kdp-${K8S_ENVIRONMENT}-deployment"
    export SECRET_TEMPDIR="${SECRET_TEMPDIR:-`mktemp -d`}"
    export SERVICE_ACCOUNT_ID="`create_service_account "${SERVICE_ACCOUNT_NAME}" "${SECRET_TEMPDIR}"`"
    export SECRET_KEYFILE="${SECRET_TEMPDIR}/key"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/container.clusterAdmin"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/container.developer"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/storage.admin"
    travis_set_env "${CONTINUOUS_DEPLOYMENT_REPO}" "SERVICE_ACCOUNT_B64_JSON_SECRET_KEY" "`cat "${SECRET_TEMPDIR}/key" | base64 -w0`"
    travis_set_env "${CONTINUOUS_DEPLOYMENT_REPO}" "K8S_ENVIRONMENT" "${K8S_ENVIRONMENT}"
    rm -rf "${SECRET_TEMPDIR}"
    travis enable --repo "${CONTINUOUS_DEPLOYMENT_REPO}"
    echo
    if ! travis env --repo "${CONTINUOUS_DEPLOYMENT_REPO}" list | grep 'DEPLOYMENT_BOT_GITHUB_TOKEN='; then
        echo
        echo " > ERROR!"
        echo
        echo " > according to GitHub policies - we are not allowed to automate creation of machine users"
        echo
        echo " > See the relevant section in devops/k8s/README.md for details"
        echo
        exit 1
    fi
    travis env --repo "${CONTINUOUS_DEPLOYMENT_REPO}" list
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-helm" ]; then
    helm init --upgrade || exit 1
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-secrets" ]; then
    if [ ! -f "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" ]; then
        echo " > missing secrets file: devops/k8s/secrets.env.${K8S_ENVIRONMENT}"
        exit 1
    fi
    kubectl delete secret env-vars
    while ! timeout 4s kubectl create secret generic env-vars --from-env-file "devops/k8s/secrets.env.${K8S_ENVIRONMENT}"; do
        sleep 1
    done
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-minio-ssl" ]; then
    if [ ! -f "devops/k8s/provision-values-${K8S_ENVIRONMENT}/letsencrypt.yaml" ]; then
        echo " > must provision let's encrypt first"
        exit 1
    fi
    NGINX_IP=`kubectl get service -o json | jq -r '.items[].status.loadBalancer.ingress[0].ip' | grep -v null`
    echo " > Please setup a domain name to point to the following IP:"
    echo " > ${NGINX_IP}"
    echo " > once done, enter the domain name below and <ENTER>"
    read -p "Domain name: " MINIO_DOMAIN
    kubectl exec -it `kubectl get pod -l app=letsencrypt -o json | jq -r '.items[0].metadata.name'` /issue_cert.sh "${MINIO_DOMAIN}"
    export VALUES_FILE="devops/k8s/provision-values-${K8S_ENVIRONMENT}/minio-ssl.yaml"
    echo "nginx:" > $VALUES_FILE
    echo "  minioSslDomain: \"${MINIO_DOMAIN}\"" >> $VALUES_FILE
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-cluster-nodes" ]; then
    if [ "${2}" == "" ]; then
        echo "usage: bin/k8s_provision.sh cluster-nodes <NUM_OF_NODES>"
        exit 1
    fi
    echo " > Provisioning ${2} additional nodes"
    gcloud container clusters resize "${CLOUDSDK_CONTAINER_CLUSTER}" "--size=${2}"
    exit 0
fi

echo " > ERROR! couldn't handle ${WHAT} ${ACTION}"
exit 2
