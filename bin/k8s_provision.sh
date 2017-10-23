#!/usr/bin/env bash

if [ "${1}" == "" ]; then
    echo "usage: bin/k8s_provision.sh <WHAT> [--list|--delete]"
    exit 1
fi

set_values() {
    bin/update_yaml.py "${1}" "devops/k8s/values-${K8S_ENVIRONMENT}-provision.yaml"
}

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
    echo " > Updating persistent disk name in values file"
    set_values '{"'$APP'": {"gcePersistentDiskName": "knesset-data-pipelines-'$K8S_ENVIRONMENT'-'$APP'"}}'
    exit 0
}

delete_disk() {
    local APP="${1}"
    echo " > Deleting persistent disk knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    gcloud compute disks delete "knesset-data-pipelines-${K8S_ENVIRONMENT}-${APP}"
    rm "devops/k8s/provision-values-${K8S_ENVIRONMENT}/${APP}.yaml"
    set_values '{"'$APP'": {"gcePersistentDiskName": null}}'
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
    source bin/k8s_connect.sh
elif [ "${K8S_ENVIRONMENT}" == "" ]; then
    export K8S_ENVIRONMENT="staging"
fi

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
        echo "Cluster will comprise of 3 g1-small machines (0.47 allocatble cpu core, 1 GB allocatble ram)"
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
            set_values '{
                "jobs": {
                    "restoreDbJobName": "db-restore-'`date +%y-%m-%d-%H-%M`'",
                    "restoreDbGsUrl": "'$GS_URL'",
                    "restoreDbServiceAccountId": "'$SERVICE_ACCOUNT_ID'",
                    "restoreDbProjectId": "'$CLOUDSDK_CORE_PROJECT'",
                    "restoreDbZone": "'$CLOUDSDK_COMPUTE_ZONE'",
                    "restoreDbServiceAccountKeySecret": "'$SECRET_NAME'"
                }
            }'
        else
            set_values '{
                "db": {
                    "backupUploadProjectId": "'$CLOUDSDK_CORE_PROJECT'",
                    "backupUploadZone": "us-central1-a",
                    "backupUploadServiceAccountId": "'$SERVICE_ACCOUNT_ID'",
                    "backupUploadServiceAccountKeySecret": "'$SECRET_NAME'",
                    "backupUploadBucketName": "'$STORAGE_BUCKET_NAME'"
                }
            }'
        fi
        exit 0
    elif [ "${ACTION}" == "--delete" ]; then
        devops/db_backup/cleanup_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}"
        exit 0
    fi

elif [ "${ACTION}-${WHAT}" == "--provision-dpp-workers" ]; then
    if [ `kubectl get nodes | grep gke- | grep dpp-workers | tee /dev/stderr | grep "[ ,]Ready[ ,]" | wc -l` == "2" ]; then
        echo " > Using existing dpp-workers node pool"
        echo " > scaling workers to 0"
        kubectl scale --replicas=0 deployment/app-workers
        echo " > draining the nodes - to ensure only the workers will be assigned to them"
        for NODE in `kubectl get nodes | grep gke- | grep dpp-workers | cut -d" " -f1 -`; do
            kubectl drain --force --ignore-daemonsets $NODE
        done
        sleep 10
        for NODE in `kubectl get nodes | grep gke- | grep dpp-workers | tee /dev/stderr | cut -d" " -f1 -`; do
            kubectl uncordon $NODE
        done
    else
        echo " > Adding workers node pool with 2 nodes n1-standard-1 (0.94 allocatble cpu cores, 2.6 GB allocatble ram)"
        if ! gcloud container node-pools create dpp-workers \
            "--cluster=${CLOUDSDK_CONTAINER_CLUSTER}" \
            --disk-size=10 \
            --machine-type=n1-standard-1 \
            --num-nodes=2; then
            exit 1
        fi
        echo " > waiting for all worker nodes to be ready and schedulable"
        while [ `kubectl get nodes | grep gke- | grep dpp-workers | grep " Ready " | wc -l` != "2" ]; do
            echo "."
            sleep 5
        done
    fi
    echo " > enabling the workers"
    set_values '{
        "app": {
            "dppWorkerConcurrency": 4,
            "dppWorkerReplicas": 2,
            "cpuRequests": 0.7,
            "memoryRequests": "1800Mi",
            "enableWorkers": true
        }
    }'
    bin/k8s_helm_upgrade.sh
    echo " > scaling workers up to 2"
    kubectl scale --replicas=2 deployment/app-workers
    kubectl rollout status deployment/app-workers
    exit 0

elif [ "${ACTION}-${WHAT}" == "--delete-dpp-workers" ]; then
    echo " > disabling the workers"
    kubectl scale --replicas=0 deployment/app-workers
    sleep 5
    set_values '{
        "app": {
            "enableWorkers": false
        }
    }'
    bin/k8s_helm_upgrade.sh
    while [ `kubectl get pods | grep app-workers- | tee /dev/stderr | wc -l` != "0" ]; do
        sleep 5
    done
    echo " > draining dpp-workers node pool"
    for NODE in `kubectl get nodes | grep gke- | grep dpp-workers | cut -d" " -f1 -`; do
        kubectl drain $NODE --force --ignore-daemonsets --grace-period=10 --timeout=15s &
    done
    sleep 20
    echo " > deleting dpp-workers node pool"
    gcloud -q container node-pools delete dpp-workers
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-metabase" ]; then
    set_values '{
        "metabase": {
            "enabled": true
        }
        "nginx": {
            "enableMetabase": true
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-grafana" ]; then
    create_disk "${DISK_SIZE:-5GB}" "influxdb"
    set_values '{
        "app": {
            "influxDb": "dpp"
        },
        "influxdb": {
            "enabled": true,
            "gcePersistentDiskName": "knesset-data-pipelines-'$K8S_ENVIRONMENT'-influxdb",
        },
        "grafana": {
            "enabled": true
        },
        "nginx": {
            "enableGrafana": true
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-grafana-anonymous" ]; then
    set_values '{
        "grafana": {
            "anonymousEnabled": true
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-shared-host" ]; then
    echo " > Ensuring all nodes support host path"
    for NODE in `kubectl get nodes | grep gke | cut -d" " -f1 -`; do
        gcloud compute ssh "${NODE}" --command "sudo mkdir -p /var/shared-host-path/{nginx-html,letsencrypt-etc,letsencrypt-log} && sudo chown -R root:root /var/shared-host-path"
    done
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-nginx" ]; then
    echo " > creating htpasswd for user 'superadmin'"
    export USERNAME=superadmin
    export TEMPDIR=`mktemp -d`
    which htpasswd > /dev/null || sudo apt-get install apache2-utils
    htpasswd -c "${TEMPDIR}/htpasswd" $USERNAME
    kubectl delete secret nginx-htpasswd
    kubectl create secret generic nginx-htpasswd --from-file "${TEMPDIR}/"
    rm -rf $TEMPDIR
    set_values '{
        "nginx": {
            "enabled": true,
            "htpasswdSecretName": "nginx-htpasswd"
        }
        "flower:" {
            "urlPrefix": "flower"
        }
    }'
    echo " > upgrading helm, and waiting for nginx service to get the load balancer iP"
    bin/k8s_helm_upgrade.sh
    while [ `kubectl get service nginx -o json  | jq -r '.status.loadBalancer.ingress[0].ip'` == "null" ]; do
        sleep 1
    done
    export NGINX_HOST_IP=`kubectl get service nginx -o json  | jq -r '.status.loadBalancer.ingress[0].ip'`
    echo " > NGINX_HOST_IP=${NGINX_HOST_IP}"
    set_values '{
        "global": {
            "rootUrl": "http://'$NGINX_HOST_IP'"
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-letsencrypt" ]; then
    set_values '{
        "letsencrypt": {
            "enabled": true
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-ssl-domain" ]; then
    NGINX_IP=`kubectl get service -o json | jq -r '.items[].status.loadBalancer.ingress[0].ip' | grep -v null`
    echo " > Please setup a domain name to point to the following IP:"
    echo " > ${NGINX_IP}"
    echo " > once done, enter the domain name below and <ENTER>"
    read -p "Domain name: " SSL_DOMAIN
    kubectl exec -it `kubectl get pod -l app=letsencrypt -o json | jq -r '.items[0].metadata.name'` /issue_cert.sh "${SSL_DOMAIN}"
    set_values '{
        "nginx": {
            "sslDomain": "'$SSL_DOMAIN'",
        "global": {
            "rootUrl": "https://'$SSL_DOMAIN'"
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-committees" ]; then
    set_values '{
        "committees": {
            "enabled": true
        },
        "nginx": {
            "enableCommittees": true
        }
    }'
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
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/compute.instanceAdmin"
    add_service_account_role "${SERVICE_ACCOUNT_ID}" "roles/iam.serviceAccountUser"
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
    NGINX_IP=`kubectl get service -o json | jq -r '.items[].status.loadBalancer.ingress[0].ip' | grep -v null`
    echo " > Please setup a domain name to point to the following IP:"
    echo " > ${NGINX_IP}"
    echo " > once done, enter the domain name below and <ENTER>"
    read -p "Domain name: " MINIO_DOMAIN
    kubectl exec -it `kubectl get pod -l app=letsencrypt -o json | jq -r '.items[0].metadata.name'` /issue_cert.sh "${MINIO_DOMAIN}"
    set_values '{
        "nginx": {
            "minioSslDomain": "'$MINIO_DOMAIN'"
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-cluster-nodes" ]; then
    if [ "${2}" == "" ]; then
        echo "usage: bin/k8s_provision.sh cluster-nodes <NUM_OF_NODES>"
        exit 1
    fi
    echo " > Setting cluster size to ${1}"
    gcloud container clusters resize "${CLOUDSDK_CONTAINER_CLUSTER}" "--size=${1}"
    echo " > Done"
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-app-autoscaler" ]; then
    if [ ! -f "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" ]; then
        echo " > You must have access to the secrets file for your environment"
        exit 1
    fi
    export AUTOSCALER_REPO=`env_config_getset "${CONTINUOUS_DEPLOYMENT_REPO}" "Github repo" CONTINUOUS_DEPLOYMENT_REPO`
    export AUTOSCALER_GIT_USER=`env_config_getset "${AUTOSCALER_GIT_USER}" "Autoscaler bot user" AUTOSCALER_GIT_USER`
    export AUTOSCALER_GIT_EMAIL=`env_config_getset "${AUTOSCALER_GIT_EMAIL}" "Autoscaler bot email" AUTOSCALER_GIT_EMAIL`
    export AUTOSCALER_BRANCH=`env_config_set "${AUTOSCALER_BRANCH}" AUTOSCALER_BRANCH master`
    if ! cat "devops/k8s/secrets.env.${K8S_ENVIRONMENT}" | grep AUTOSCALER_GITHUB_TOKEN; then
        echo
        echo " > according to GitHub policies - we are not allowed to automate creation of machine users"
        echo
        echo " > See the relevant section in devops/k8s/README.md regarding continuous deployment"
        echo
        echo " > You should get a token, and input it here"
        read -p "Autoscaler Token: " AUTOSCALER_TOKEN
        echo " > Updating secretes"
        echo >> devops/k8s/secrets.env.production
        echo "AUTOSCALER_GITHUB_TOKEN=${AUTOSCALER_TOKEN}" >> devops/k8s/secrets.env.production
        bin/k8s_provision.sh secrets
    fi
    set_values '{
        "app": {
            "enableAutoscaler": true,
            "autoscalerInterval": "300",
            "autoscalerPipelinesUrl": "http://app-serve:5000",
            "autoscalerRepo": "'$AUTOSCALER_REPO'",
            "autoscalerGitUser": "'$AUTOSCALER_GIT_USER'",
            "autoscalerGitEmail": "'$AUTOSCALER_GIT_EMAIL'",
            "autoscalerBranch": "'$AUTOSCALER_BRANCH'"
        }
    }'
    exit 0

elif [ "${ACTION}-${WHAT}" == "--provision-ssh-socks-proxy" ]; then
    TEMPDIR=`mktemp -d`
    export SSH_SOCKS_PROXY_HOST=`env_config_getset "${SSH_SOCKS_PROXY_HOST}" "SSH Host" SSH_SOCKS_PROXY_HOST`
    export SSH_SOCKS_PROXY_PORT=`env_config_getset "${SSH_SOCKS_PROXY_PORT}" "SSH Port" SSH_SOCKS_PROXY_PORT`
    export SSH_SOCKS_PROXY_KEY_COMMENT=`env_config_getset "${SSH_SOCKS_PROXY_KEY_COMMENT}" "Proxy key comment" SSH_SOCKS_PROXY_KEY_COMMENT`
    export SSH_SOCKS_PROXY_AUTHORIZED_KEYS=`env_config_getset "${SSH_SOCKS_PROXY_AUTHORIZED_KEYS}" "Authorized keys location in ssh host" SSH_SOCKS_PROXY_AUTHORIZED_KEYS`
    export SSH_SOCKS_PROXY_SOCKS_PORT=`env_config_getset "${SSH_SOCKS_PROXY_SOCKS_PORT}" "Socks port" SSH_SOCKS_PROXY_SOCKS_PORT`
    export SSH_SOCKS_PROXY_HOST_KEYFILE=`env_config_getset "${SSH_SOCKS_PROXY_HOST_KEYFILE}" "Key file on host for authentication to ssh server" SSH_SOCKS_PROXY_HOST_KEYFILE`
    PROJECT_DIR=`pwd`
    pushd $TEMPDIR >/dev/null
        curl -L  https://github.com/OriHoch/ssh-socks-proxy/archive/master.tar.gz | tar xvz
        cd ssh-socks-proxy-master
        echo "SSH_HOST=${SSH_SOCKS_PROXY_HOST}" >> .env
        echo "SSH_PORT=${SSH_SOCKS_PROXY_PORT}" >> .env
        echo "KEY_COMMENT=${SSH_SOCKS_PROXY_KEY_COMMENT}" >> .env
        echo "AUTHORIZED_KEYS=${SSH_SOCKS_PROXY_AUTHORIZED_KEYS}" >> .env
        echo "SOCKS_PORT=${SSH_SOCKS_PROXY_SOCKS_PORT}" >> .env
        cp -f "${SSH_SOCKS_PROXY_HOST_KEYFILE}" ./ssh-host.key
        echo "SSH_OPTS=-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /upv/workspace/ssh-host.key" >> .env
        ./upv.sh . pull .
        ./upv.sh . provision
        eval `dotenv list`
        kubectl delete secret ssh-socks-proxy
        while ! timeout 4s kubectl create secret generic ssh-socks-proxy --from-env-file ".env"; do
            sleep 1
        done
    popd >/dev/null
    set_values '{
        "app": {
            "sshSocksProxyUrl": "socks5h://ssh-socks-proxy:'${SSH_SOCKS_PROXY_SOCKS_PORT}'"
        },
        "ssh-socks-proxy": {
            "enabled": true,
            "ssh_host": "'${SSH_SOCKS_PROXY_HOST}'",
            "ssh_port": "'${SSH_SOCKS_PROXY_PORT}'",
            "socks_port": "'${SSH_SOCKS_PROXY_SOCKS_PORT}'"
        }
    }'
    exit 0

fi

echo " > ERROR! couldn't handle ${WHAT} ${ACTION}"
exit 2
