# Knesset Data Pipelines Kubernetes Environment

## Setting up a staging cluster - for local testing / development

### Prerequisites

* Management of the environment was tested using Ubuntu 17.10 but should work on other similar Linux OS.
* Install the gcloud cli and get permissions on a Google project with billing (you should have the Google project id)
* Fork / Clone the knesset-data-pipelines repository
* All commands should run from the root of the knesset-data-pipelines project repository, with authenticated gcloud cli

### Create the cluster

This will create a standard staging cluster for infrastructure development and testing.

Running the script will show the deployment details and require to input a billable google project id before creating the cluster.

* `bin/k8s_create.sh`

### Pre-Deployment

This steps should be done before first deployment:

* Build the images and push to the private google docker registry
  * `bin/k8s_build_push.sh`
* Initialize helm
  * `helm init --upgrade`
* Create the secrets
  * `bin/k8s_recreate_secrets.sh`

### Deployment

* `bin/k8s_helm_upgrade.sh`

### Post-Deployment

The helm upgrade script doesn't always restart pods, depending on the changes made.

Bear in mind that some services might take a while to start, so be patient before panicking that something doesn't work.

If you find that a service or pod doesn't start, or to debug:

* Connect to the relevant environment and setup kubectl bash autocompletion
  * `source bin/k8s_connect.sh`
* Check the pods - all should be RUNNING
  * `kubectl get pods`
  * Drill down to a specific pod
    * `kubectl describe <TAB><TAB>`
* Force update of a specific deployment:
  * `bin/k8s_force_update.sh <DEPLOYMENT_NAME>`
* Wait for rollout of a specific deployment
  * `kubectl rollout status deployment <TAB><TAB>`
* Do a hard-reset to ensure everything is deployed:
  * `bin/k8s_hard_reset.sh`

## Available cluster internal endpoints

Keep the proxy running the background

* `source bin/k8s_connect.sh`
* `kubectl proxy`

With default staging environment configuration you should have access to the following endpoints:

* Kubernetes UI: http://localhost:8001/ui
* Pipelines dashboard: http://localhost:8001/api/v1/namespaces/default/services/app/proxy/
* Adminer (DB UI): http://localhost:8001/api/v1/namespaces/default/services/adminer/proxy/
  * System: PostgreSQL
  * Server: db
  * Username: postgres
  * Password: 123456
  * Database: app
* Flower (Celery management): http://localhost:8001/api/v1/namespaces/default/services/flower/proxy/

You can use the following snippet to open all endpoints in Google Chrome:

* `google-chrome http://localhost:8001/ui http://localhost:8001/api/v1/namespaces/default/services/app/proxy/ http://localhost:8001/api/v1/namespaces/default/services/adminer/proxy/ http://localhost:8001/api/v1/namespaces/default/services/flower/proxy/`

## Enabling additional services / custom configuration

The default staging environment is minimal, to enable additional services:

* Create custom values file (make sure it's not committeed to Git)
  * `touch devops/k8s/values-staging.yaml`
* Append configurations to the file, according to the following sections
* Follow the deployment and post-deployment procedures above

### Running pipeline workers

```
app:
  dppWorkerConcurrency: 1
```

The default staging environment runs with 0 pipeline workers - this means data will not be gathered and aggregated.

For staging or low cpu environment you shouldn't enable more then 1 worker.

Once you enable the worker, scheduled pipelines should start running automatically

You can also schedule a pipeline manually to run on the workers using this snippet:

```kubectl exec `kubectl get pod -l app=app -o json | jq -r '.items[0].metadata.name'` -- bin/execute_scheduled_pipeline.sh ./committees/kns_committee```

### Metabase - user friendly DB UI

```
metabase:
  enabled: true
```

depends on DB for persistency (database name = metabase)

on first run, log-in to set the admin user password:

http://localhost:8001/api/v1/namespaces/default/services/metabase/proxy/

You can add a database using the same configuration detailed above for Adminer

### Visualize pipeline metrics in Grafana (Via InfluxDB)

```
app:
  influxDb: dpp

influxdb:
  enabled: true
  # persistent disk is optional - if you leave it commented it means it will loose historical metrics on every new pod - which should be fine for staging environment
  # gcePersistentDiskName: knesset-data-pipelines-staging-influxdb

grafana:
  enabled: true
```

Once deployed, do the initial Grafana setup:

* http://localhost:8001/api/v1/namespaces/default/services/grafana/proxy/
* default login is `admin:admin`
* Add a datasource:
  * Name: influxdb
  * Type: InfluxDB
  * Url: http://influxdb:8086/
  * Access: Proxy
  * Database: dpp
* In Grafana web UI - go to Dashboards > Import
  * Import the dashboard from `devops/grafana_dataservice_processors_dashboard.json`

### Enable shared host path - to allow sharing paths between nginx, let's encrypt and app pods

the shared host path hack allows simple shared directories between pods

first, get the name of the current node nginx is running - to use it as the shared host path:

```
source bin/k8s_connect.sh
export SHARED_HOST_NAME=`kubectl get pod -l app=nginx -o json | jq -r '.items[0].spec.nodeName'`
```

Create the required directories on the node:

```
gcloud compute ssh $SHARED_HOST_NAME --command "sudo mkdir -p /var/shared-host-path/{nginx-html,letsencrypt-etc,letsencrypt-log,app-data} && sudo chown -R root:root /var/shared-host-path"
```

Enable the shared host - which mounts the path and ensure all pods are on the same node:

```
global:
  # to get the current nginx node name:
  # kubectl get pod -l app=nginx -o json | jq -r '.items[0].spec.nodeName'
  sharedHostName: <SHARED_HOST_NAME>
```


### Nginx

```
nginx:
  enabled: true

  # you should explicitly enable / disable sub-service mount points depending on services you run
  enableData: true
  enablePipelines: true
  enableFlower: true
  enableAdminer: true
  # enableMetabase: true
  # enableGrafana: true

flower:
    # when flower is used with nginx, this is required
    # it will then stop working properly on the localhost proxy
    urlPrefix: flower
```

Once service started and has external IP, you need to update the global rootUrl value which is used to get proper url to services:

```
global:
  # to get the nginx load balancer ip:
  # kubectl get service nginx -o json  | jq -r '.status.loadBalancer.ingress[0].ip'
  rootUrl: http://1.2.3.4
```

You can use the following to open the core services in google chrome:

```
source bin/k8s_connect.sh
export NGINX_HOST=`kubectl get service nginx -o json | jq '.status.loadBalancer.ingress[0].ip' -r`
google-chrome "${NGINX_HOST}/pipelines" "${NGINX_HOST}/adminer" "${NGINX_HOST}/flower"
```

Flower and Adminer services should not be publically exposed, to enable restricted access -

Create an htpasswd file:

```
export USERNAME=superadmin
export TEMPDIR=`mktemp -d`
which htpasswd > /dev/null || sudo apt-get install apache2-utils
htpasswd -c "${TEMPDIR}/htpasswd" $USERNAME
```

Create a secret based on it and cleanup:

```
kubectl create secret generic nginx-htpasswd --from-file "${TEMPDIR}/"
rm -rf $TEMPDIR
kubectl describe secret nginx-htpasswd
```

Enable by setting the secret name in the values file:

```
nginx:
  htpasswdSecretName: nginx-htpasswd
```

Insecure services like Adminer / Flower will now be password protected

You should also enable SSL - otherwise password is sent in clear-text:

You must enable the shared host feature - see above

Enable the let's encrypt pod which issues and renew certificates

```
letsencrypt:
  enabled: true
```

Setup DNS to your load balancer IP and issue a certificate:

```
source bin/k8s_connect.sh
kubectl exec -it `kubectl get pod -l app=letsencrypt -o json | jq -r '.items[0].metadata.name'` /issue_cert.sh your.domain.com
```

enable nginx and other services to use the secure domain:

```
nginx:
  sslDomain: your.domain.com

global:
  rootUrl: https://your.domain.com
```

When shared host is enabled, app will also be forced to select the shared host node

This allows nginx to serve data files generated by the pipelines, these are available at:

http://your.domain.com/data/
http://your.domain.com/data-json/

### Committees Webapp

You should build and push the committees webapp:

`bin/k8s_build_push.sh --committees`

enable it:

```
committees:
  enabled: true

nginx:
  enableCommittees: true
```

### Forcing DB pod to use the same node

DB and App have persistent disks which might take a bit of time to be released when restarting pods.

App is already selected for the hostpath node - so it should be fine

You can set the DB to use the same node

```
db:
  # to get the current node db pos is attached to:
  # kubectl get pod -l app=db -o json | jq -r '.items[0].spec.nodeName'
  # make sure it's different then the shared host node - not to overload a single node
  nodeSelectorHostname: <HOST_NAME>
```

### Upload daily DB backups to google cloud storage

We use google service accounts to provide limited access to upload backups from a pod:

```
db:
  # google cloud project id
  backupUploadProjectId: ""
  # google cloud zone
  backupUploadZone: us-central1-a
  # create a new service account:
  # export SERVICE_ACCOUNT_NAME="knesset-data-db-backup-upload"
  # gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}"
  # export SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_NAME}@${CLOUDSDK_CORE_PROJECT}.iam.gserviceaccount.com"
  # echo $SERVICE_ACCOUNT_ID
  backupUploadServiceAccountId: <replace with the service account id>
  # create a key allows this service account to add objects to storage buckets and add it as a k8s secret:
  # export UPLOAD_KEY_SECRET_NAME="db-backup-upload-google-key"
  # gcloud iam service-accounts keys create "--iam-account=${SERVICE_ACCOUNT_ID}" "${SERVICE_ACCOUNT_NAME}.google-secret-key"
  # gcloud --quiet  projects add-iam-policy-binding "${CLOUDSDK_CORE_PROJECT}" "--member=serviceAccount:${SERVICE_ACCOUNT_ID}" "--role=roles/storage.objectCreator"
  # kubectl create secret generic ${UPLOAD_KEY_SECRET_NAME} --from-file "${SERVICE_ACCOUNT_NAME}.google-secret-key"
  # rm "${SERVICE_ACCOUNT_NAME}.google-secret-key"
  backupUploadServiceAccountKeySecret: db-backup-upload-google-key
  # google cloud storage bucket name, you should create it beforehand:
  # gsutil mb gs://knesset-data-pipelines-staging-db-backups/
  # and give permissions for the service account on this bucket:
  # gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT_ID}:objectCreator,objectViewer,objectAdmin" "gs://knesset-data-pipelines-staging-db-backups"
  backupUploadBucketName: knesset-data-pipelines-staging-db-backups
```



## Common tasks, issues, tips and tricks

### Updating app image

* This script builds and pushes all images automatically:
  * `bin/k8s_build_push.sh`
  * This builds the images and pushes to current google project private repository
  * It creates a values files with the tagged version
  * This files is used automatically by the bin/k8s_deploy.sh script
* You can inspect the script to build / push images differently

### Google Authentication

You might need to do this from time to time to reauth with google

* `source bin/k8s_connect.sh`
* `gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER`

### DB Backup

