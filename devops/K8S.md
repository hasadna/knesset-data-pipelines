# Setting knesset-data environment on Kubernetes

## connecting to the Kubernetes cluster

We are currently using Google Container Engine (Kubernetes)

You need to get permissions on the project (`id=hasadna-oknesset`)

Once you have permissions and gcloud installed you should be able to run:
* `gcloud container clusters get-credentials hasadna-oknesset --zone us-central1-a --project hasadna-oknesset`
* `kubectl proxy`

Kubernetes UI should be available at http://localhost:8001/ui

## Initial setup

* `kubectl get nodes`
  * should have 1 or more nodes with supported k8s version (tested with v1.6.7 - on GKE)
* `cp devops/k8s_configmap{.example,}.yaml`
* edit devops/k8s_configmap.yaml and set proper values
* `bin/k8s_apply.sh`

## Deploying infrastructure changes

* edit or pull changes to relevant files under devops/k8s
* `bin/k8s_apply.sh`

## Deploying code changes

* `bin/k8s_deploy.sh <deploynemt_name> <image_suffix>`

Some examples:

* `bin/k8s_deploy.sh app pipelines:latest`
* `bin/k8s_deploy.sh app pipelines:v1.0.4`
* `bin/k8s_deploy.sh nginx nginx:v1.0.4`
* `bin/k8s_deploy.sh letsencrypt letsencrypt:v1.0.4`

## Common Tasks

### runnning pipelines commands in the app pod

* get the name of the app pod
  * `kubectl get pods`
* run committee meeting pipelines, overriding some env vars:
  * `kubectl exec <app_pod_name> -- bash -c "OVERRIDE_COMMITTEE_MEETING_FROM_DAYS=-8000 OVERRIDE_COMMITTEE_IDS=2 dpp run ./committees/committee-meetings"`
* schedule the committee meeting protocols pipeline to run immediately
  * `kubectl exec <app_pod_name> -- /knesset/bin/execute_scheduled_pipeline.sh ./committees/committee-meeting-protocols`
* initialize the pipelines status (in case of "stuck" job)
  * `kubectl exec <app_pod_name> -- dpp init`
* running an interactive bash session
  * `kubectl exec -it <app_pod_name> -- bash`
* running celery python shell
  * `kubectl exec -it <app_pod_name> -- python3 -m celery -b redis://redis:6379/6 -A datapackage_pipelines.app shell`
* running flower
  * `kubectl exec <app_pod_name> -- pip install flower`
  * `kubectl exec <app_pod_name> -- python3 -m celery -b redis://redis:6379/6 -A datapackage_pipelines.app flower`

### editing files locally on the kubernetes node

* we have some local files on the kubernetes host, you might need to edit / view them directly
  * ssh to the host
    * `gcloud compute ssh --project=hasadna-oknesset gke-hasadna-oknesset-default-pool-527f395d-1zm9 --zone us-central1-a`
  * files are in /var/next-oknesset
    * `ls /var/next-oknesset`
