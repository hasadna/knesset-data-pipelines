# Knesset Data Pipelines Kubernetes Environment

## Setting up a new cluster

### Prerequisites

* Management of the environment was tested using Ubuntu 17.10 but should work on other similar Linux OS.
* Install the gcloud cli and get permissions on a Google project with billing (you should have the Google project id)
* Fork / Clone the knesset-data-pipelines repository
* All commands should run from the root of the knesset-data-pipelines project repository, with authenticated gcloud cli

### Install helm client (locally)

* `bin/install_helm.sh`

### Create the cluster

This will create a standard staging cluster for infrastructure development and testing.

Running the script will show the deployment details and require to input a billable google project id before creating the cluster.
* `bin/k8s_provision.sh cluster`

Deploy the knesset-data-pipelines Helm release:
* `bin/k8s_helm_upgrade.sh`

## Debugging

Bear in mind that some services might take a while to start, so be patient before panicking that something doesn't work.

The helm upgrade script doesn't always restart pods, depending on the changes made.

Open the Kubernetes dashboard
* `bin/k8s_proxy.sh & google-chrome http://localhost:8001/ui`

Force update of a deployment:
* `bin/k8s_force_update.sh <DEPLOYMENT_NAME>`

Do a hard-reset to ensure everything is deployed (causes significant down-time):
* `bin/k8s_hard_reset.sh`

Connect to the relevant environment, use kubectl bash autocompletion to debug
* Check the pods
  * `kubectl get pods`
* Drill down to a specific pod
  * `kubectl describe <TAB><TAB>`
* Wait for rollout of a specific deployment
  * `kubectl rollout status deployment <TAB><TAB>`
* explore the Kubectl cli
  * `kubectl <TAB><TAB>`

## Available cluster internal endpoints

Using the Kubernetes proxy you can access internal services

Run the proxy:

* `bin/k8s_proxy.sh`

With the default minimal environment you should have access to the following endpoints:

* Kubernetes UI: http://localhost:8001/ui
* Pipelines dashboard: http://localhost:8001/api/v1/namespaces/default/services/app/proxy/
* Adminer (DB UI): http://localhost:8001/api/v1/namespaces/default/services/adminer/proxy/
  * System: PostgreSQL
  * Server: db
  * Username: postgres
  * Password: 123456
  * Database: app
* Flower (Celery management): http://localhost:8001/api/v1/namespaces/default/services/flower/proxy/

You can access other Kubernetes services, just use the following template:
* `http://localhost:8001/api/v1/namespaces/default/services/<K8S_SERVICE_NAME>/proxy/`

You can use the following snippet to open all default endpoints in Google Chrome:

* `google-chrome http://localhost:8001/ui http://localhost:8001/api/v1/namespaces/default/services/app/proxy/ http://localhost:8001/api/v1/namespaces/default/services/adminer/proxy/ http://localhost:8001/api/v1/namespaces/default/services/flower/proxy/`

## Additional services / custom configuration

### Restoring from DB backup

If you have a DB backup, now is a good time to restore from it - before starting additional services which complicates it

Pay attention that this db dump contains sensitive details, so do not publically expose it.

If you don't have a gs url but have a dump file locally, run the following:

```
source bin/k8s_connect.sh
export STORAGE_BUCKET_NAME="kdp-${K8S_ENVIRONMENT}-db-backups"
gsutil mb "gs://${STORAGE_BUCKET_NAME}"
gsutil cp -Z dump.sql "gs://${STORAGE_BUCKET_NAME}/dump.sql"
```

Provision the db restore resources

```
GS_URL="<google storage url with an sql dump>" bin/k8s_provision.sh db-restore
bin/k8s_helm_upgrade.sh
```

Once restore is complete, you might need to setup the services:

* Metabase -
  * google login won't work if you have different domain, you can do a forgot password procedure - and should get the email from next.oknesset.org
  * **because mail settings are in metbase DB**
  * once logged-in, you might also need to change the db password
* Grafana -
  * simple enough to re-setup if you have problems


### Running pipeline workers

The default environment doesn't run any workers, this provisions 1 worker:

```
bin/k8s_provision.sh dpp-workers
bin/k8s_helm_upgrade.sh
```

### Metabase - user friendly DB UI

```
bin/k8s_provision.sh metabase
bin/k8s_helm_upgrade.sh
```

depends on DB for persistency (database name = metabase)

on first run, log-in to set the admin user password:

http://localhost:8001/api/v1/namespaces/default/services/metabase/proxy/

You can add a database using the same configuration detailed above for Adminer

### Visualize pipeline metrics in Grafana (Via InfluxDB)

```
bin/k8s_provision.sh grafana
bin/k8s_helm_upgrade.sh
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

```
bin/k8s_provision.sh shared-host
bin/k8s_helm_upgrade.sh
```

### Nginx

Expose services via paths on a load balancer, supports ssl and http password

```
bin/k8s_provision.sh nginx
bin/k8s_helm_upgrade.sh
```

You can use the following to open the core services in google chrome:

```
source bin/k8s_connect.sh
export NGINX_HOST=`kubectl get service nginx -o json | jq '.status.loadBalancer.ingress[0].ip' -r`
google-chrome "${NGINX_HOST}/pipelines" "${NGINX_HOST}/adminer" "${NGINX_HOST}/flower"
```

### Let's encrypt

```
bin/k8s_provision.sh letsencrypt
bin/k8s_helm_upgrade.sh
```

#### Issuing a new certificate

Setup DNS to your load balancer IP and issue a certificate:

```
export SSL_DOMAIN="your.dmain.com"
source bin/k8s_connect.sh
kubectl exec -it `kubectl get pod -l app=letsencrypt -o json | jq -r '.items[0].metadata.name'` /issue_cert.sh "${SSL_DOMAIN}"
```

If you provision let's encrypt again with SSL_DOMAIN environment variable - it will use it

```
bin/k8s_provision.sh letsencrypt
bin/k8s_helm_upgrade.sh
google-chrome "https://${SSL_DOMAIN}/pipelines" "https://${SSL_DOMAIN}/adminer" "https://${SSL_DOMAIN}/flower" "https://${SSL_DOMAIN}/data" "https://${SSL_DOMAIN}/data-json"
```

#### Importing existing certificate

```
export SSL_DOMAIN="domain.com"
# from other cluster
mkdir -p ./etc-letsencrypt-bak
kubectl cp letsencrypt-3851873296-ffljt:/etc/letsencrypt ./etc-letsencrypt-bak/letsencrypt
# from this cluster
source bin/k8s_connect.sh
kubectl cp ./etc-letsencrypt-bak/letsencrypt letsencrypt-3851873296-ffljt:/etc/
kubectl exec -it letsencrypt-797647080-9n2vn bash -- -c "cd /etc/letsencrypt/live/ && rm -f "${SSL_DOMAIN}/*" && cd $SSL_DOMAIN && ln -s "../../archive/${SSL_DOMAIN}/cert1.pem" cert.pem && ln -s "../../archive/${SSL_DOMAIN}/chain1.pem" chain.pem && ln -s "../../archive/${SSL_DOMAIN}/fullchain1.pem" fullchain.pem && ln -s "../../archive/${SSL_DOMAIN}/privkey1.pem" privkey.pem"
bin/k8s_provision.sh letsencrypt
```

### Committees Webapp

```
bin/k8s_provision.sh committees
bin/k8s_helm_upgrade.sh
google-chrome "https://${SSL_DOMAIN}/committees"
```

### Upload daily DB backups to google cloud storage

```
bin/k8s_provision.sh db-backup
bin/k8s_helm_upgrade.sh
```

### Continuous Deployment

```
bin/k8s_provision.sh continuous-deployment
bin/k8s_helm_upgrade.sh
```

According to GitHub policies, we are not allowed to automate creation of machine users.

Please proceed according to the instructions [here](https://developer.github.com/v3/guides/managing-deploy-keys/#machine-users)

You need to get a personal access token for this machine user, with public_repo access permission

Add this machine user as collaborator with write access to your project"

You can add a collaborator from the api:"
* `curl -u YourGithubUserName https://api.github.com/repos/${CONTINUOUS_DEPLOYMENT_REPO}/collaborators/MACHINE_USER_NAME -X PUT"`

Finally, set the token in Travis:
* `travis env --repo ${CONTINUOUS_DEPLOYMENT_REPO} --private --org set DEPLOYMENT_BOT_GITHUB_TOKEN \"${TOKEN}\""`

A push to master branch should now cause deployment
* `git checkout master`
* `echo " " >> README.md`
* `git add README.md`
* `git push origin master`



## Common tasks, issues, tips and tricks

### Updating app image

* This script builds and pushes all images automatically:
  * `bin/k8s_build_push.sh`
  * This builds the images and pushes to current google project private repository
  * It creates a values files with the tagged version

### Google Authentication

You might need to do this from time to time to reauth with google

* `source bin/k8s_connect.sh`
* `gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER`

### Getting a DB backup from non-helm installations

Sometime you have a DB not in the cluster, the following can be used to run the backup daemon on it and get the gs url

```
export DATE=`date +%y-%m-%d-%H-%M`
export CLOUDSDK_CORE_PROJECT=""
export CLOUDSDK_CONTAINER_CLUSTER=""
export PGPASSWORD=""
export PGHOST="db"
export SERVICE_ACCOUNT_NAME="knesset-data-db-backup-upload"
export STORAGE_BUCKET_NAME="knesset-data-pipelines-staging-db-backups"
export CLOUDSDK_COMPUTE_ZONE="us-central1-a"
export TAG="gcr.io/${CLOUDSDK_CORE_PROJECT}/knesset-data-pipelines-db-backup:v0.0.0-${DATE}"
devops/db_backup/cleanup_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}"
source <(devops/db_backup/provision_resources.sh "${SERVICE_ACCOUNT_NAME}" "${STORAGE_BUCKET_NAME}")
docker build -t "${TAG}" devops/db_backup
gcloud docker -- push "${TAG}"
gcloud container clusters get-credentials $CLOUDSDK_CONTAINER_CLUSTER
kubectl run "db-backup-${DATE}" --image="${TAG}" \
    --env "PGPASSWORD=${PGPASSWORD}" \
    --env "PGHOST=${PGHOST}" \
    --env "PGPORT=5432" \
    --env "PGUSER=postgres" \
    --env "GOOGLE_AUTH_SECRET_KEY_B64_JSON=`cat $SECRET_KEY_FILE | base64 -w0`" \
    --env "SERVICE_ACCOUNT_ID=${SERVICE_ACCOUNT_ID}" \
    --env "CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT}" \
    --env "CLOUDSDK_COMPUTE_ZONE=${CLOUDSDK_COMPUTE_ZONE}" \
    --env "STORAGE_BUCKET_NAME=${STORAGE_BUCKET_NAME}" \
    --env "BACKUP_INITIAL_DELAY_SECONDS=1"
```

Check the pod logs for the gs url

```
kubectl logs `kubectl get pods | grep "db-backup-${DATE}" | cut -d" " -f1 -`
```

If it's in the same project, use it directly, otherwise, download and re-upload where needed with `gsutil cp -Z`

### runnning pipelines commands in the app pod

* get the name of the app pod
  * `kubectl get pods`
* run committee meeting pipelines, overriding some env vars:
  * `kubectl exec <app_pod_name> -- bash -c "OVERRIDE_COMMITTEE_MEETING_FROM_DAYS=-8000 OVERRIDE_COMMITTEE_IDS=2 dpp run ./committees/committee-meetings"`
* schedule the committee meeting protocols pipeline to run immediately
  * `kubectl exec <app_pod_name> -- /knesset/bin/execute_scheduled_pipeline.sh ./committees/committee-meeting-protocols`
* initialize the pipelines status
  * `kubectl exec <app_pod_name> -- dpp init`
* running an interactive bash session
  * `kubectl exec -it <app_pod_name> -- bash`
* running celery python shell
  * `kubectl exec -it <app_pod_name> -- python3 -m celery -b redis://redis:6379/6 -A datapackage_pipelines.app shell`

### Debugging pipeline tasks

* you can review and revoke tasks in flower - https://next.oknesset.org/flower/
* schedule a task to run immediately (you need to do this after revoking a task - to re-run it)
  * `kubectl exec `kubectl get pods | grep app- | cut -d" " -f1 -` bin/execute_scheduled_pipeline.sh <PIPELINE_ID>`
* update tasks (runs every minute, but you can scheduled to run immediately as well)
  * ```kubectl exec `kubectl get pods | grep app- | cut -d" " -f1 -` bin/update_pipeline_status.sh```

### Exporting all committees data from DB

This export is used by knesset-data-committees-webapp

```
kubectl exec -it db-87339143-v3mpl -- bash -c "sudo -u postgres pg_dump -t kns_committee -t kns_jointcommittee -t kns_cmtsitecode -t kns_committeesession -t kns_cmtsessionitem -t kns_documentcommitteesession > /committees_db_dump.sql"
kubectl cp db-87339143-v3mpl:/committees_db_dump.sql ./committees_db_dump.sql
```

### Developing on production

Workers are very CPU intensive, so best to disable them when doing development
* `bin/k8s_helm_upgrade.sh --set app.dppWorkerConcurrency=0`

General development workflow:

1. Make changes to the code, build from the local directory: `BUILD_LOCAL=1 bin/k8s_build_push.sh --app`
2. Deploy -  `bin/k8s_helm_upgrade.sh --set app.dppWorkerConcurrency=0 --recreate-pods`
3. Ssh into a pod - ```kubectl exec -it `kubectl get pods | grep app- | cut -d" " -f1 -` -- bash```
  * Schedule a pipeline - `bin/execute_scheduled_pipeline.sh <PIPELINE_ID>`
  * Run a pipeline directly = `dpp run <PIPELINE_ID>`
4. Go back to 1 / commit to deploy (you should only commit code changes, not image ids)
