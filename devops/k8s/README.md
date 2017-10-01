# Knesset Data Pipelines Kubernetes Environment

## Setting up a staging cluster - for local testing, experimantation and discovery

### Prerequisites

* Management of the environment was tested using Ubuntu 17.10 but should work on other similar Linux OS.
* Install the gcloud cli and get permissions on a Google project with billing (you should have the Google project id)
* Fork / Clone the knesset-data-pipelines repository
* All commands should run from the root of the knesset-data-pipelines project repository, with authenticated gcloud cli

## Create the cluster

This will create a standard staging cluster for infrastructure development and testing.

Running the script will show the deployment details and require to input a billable google project id before creating the cluster.

* `bin/k8s_create.sh`

## Pre-Deployment

This steps should be done on first deployment:

* Build the images and push to the private google docker registry
  * `bin/k8s_build_push.sh`
* Initialize helm
  * `helm init --upgrade`
* Create the secrets
  * `bin/k8s_recreate_secrets.sh`

## Deployment

* `bin/k8s_helm_upgrade.sh`

## Post-Deployment

* Connect to the relevant environment and setup kubectl bash autocompletion
  * `source bin/k8s_connect.sh`
* Check the pods - all should be RUNNING
  * `kubectl get pods`
  * Drill down to a specific pod
    * `kubectl describe <TAB><TAB>`
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

* Create custom values file (make sure it's not committeed to Git):
  * `test ! -f devops/k8s/values-staging.yaml && cp devops/k8s/values-staging{.example,}.yaml`
* Edit the file
  * `devops/k8s/values-staging.yaml`
* Follow the comments in that file and uncomment / modify as needed

Just remember that when you run the deploy again without this parameter - environment will return to minimal state

## Running pipeline workers

The default staging environment runs with 0 pipeline workers - this means data will not be gathered and aggregated.

* start a single worker:
  * `bin/k8s_deploy.sh --set app.dppWorkerConcurrency=1`
  * Pipelines should start running, you can follow status in the [Pipelines Dashboard](http://localhost:8001/api/v1/namespaces/default/services/app/proxy/)
* You can schedule a specific pipeline to run using:
  * `source bin/k8s_connect.sh && kubectl exec -it app-<TAB><TAB> -- bin/execute_scheduled_pipeline.sh ./committees/kns_committee`

### Metabase - user friendly DB UI

* Start a single pipeline worker with Metabase to visualize the data in DB
  * `bin/k8s_deploy.sh --set app.dppWorkerConcurrency=1,metabase.enabled=true`
* on first run, log-in to set the admin user password
  * http://localhost:8001/api/v1/namespaces/default/services/metabase/proxy/
* Set up a database using the same configuration you used for Adminer

### Visualize pipeline metrics in Grafana (Via InfluxDB)

* Start a single pipeline worker along with influxDB and grafana
  * `bin/k8s_deploy.sh --set app.dppWorkerConcurrency=1,influxdb.enabled=true,app.influxDb=dpp,grafana.enabled=true`
* Initial Grafana setup
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
* To force some pipelines to run (to get metrics):
  * `source bin/k8s_connect.sh`
  * `kubectl exec -it app-<TAB><TAB> -- bin/execute_scheduled_pipeline.sh ./committees/kns_committee`
  * You should see some metrics in Grafana in a few seconds

### Nginx

publically exposes services via K8S LoadBalancer

* Start the default environment with nginx
  * `bin/k8s_deploy.sh --set nginx.enabled=true,flower.urlPrefix=flower`
* Once service started and has external IP, you can save the IP in you environment's .env file
  * `source bin/k8s_connect.sh`
  * ```echo "NGINX_HOST=`kubectl get service nginx -o json | jq '.status.loadBalancer.ingress[0].ip' -r`" >> "devops/k8s/.env.${K8S_ENVIRONMENT}"```
  * `source/bin/k8s_connect.sh`
* Services are available as subpaths of the nginx host
  * If you have Google Chrome and configured the NGINX_HOST environment variable, you can use the following command to open all endpoints:
    * `google-chrome "${NGINX_HOST}/pipelines" "${NGINX_HOST}/adminer" "${NGINX_HOST}/flower"`

## Common tasks and issues

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
