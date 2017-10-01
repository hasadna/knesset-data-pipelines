# knesset-data-pipelines kubernetes environment

## connecting to the Kubernetes cluster

We are currently using Google Container Engine (Kubernetes)

You need to get permissions on the project (`id=hasadna-oknesset`)

Once you have permissions and gcloud installed you should be able to run:
* `bin/k8s_proxy.sh`

Kubernetes UI should be available at http://localhost:8001/ui

## Continuous Deployment

Every push to master updates the k8s configurations on the cluster

This is done using travis, which eventually runs `bin/k8s_deploy.sh`

### Updating images (Deploying application changes)

* google container registry builds images on every push to master
* images are tagged based on commit sha - which you refer to from the relevantk8s configuration image attribute
* travis deploy script automatically commits and pushed a change to the latest image

## Common Tasks

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
* running flower
  * `kubectl exec <app_pod_name> -- pip install flower`
  * `kubectl exec <app_pod_name> -- python3 -m celery -b redis://redis:6379/6 -A datapackage_pipelines.app flower`

### editing files locally on the kubernetes node

* we have some local files on the kubernetes host, you might need to edit / view them directly
  * ssh to the host
    * `gcloud compute ssh --project=hasadna-oknesset gke-hasadna-oknesset-default-pool-527f395d-1zm9 --zone us-central1-a`
  * files are in /var/next-oknesset
    * `ls /var/next-oknesset`

### Debugging pipeline tasks

* you can review and revoke tasks in flower - https://next.oknesset.org/flower/
* schedule a task to run immediately (you need to do this after revoking a task - to re-run it)
  * `kubectl exec <app_pod_name> -- /knesset/bin/execute_scheduled_pipeline.sh <PIPELINE_ID>`
* update tasks (runs every minute, but you can scheduled to run immediately as well)
  * `kubectl exec <app_pod_name> -- /knesset/bin/update_pipeline_status.sh`

### Exporting all committees data from DB

This export is used by knesset-data-committees-webapp

```
kubectl exec -it db-87339143-v3mpl -- bash -c "sudo -u postgres pg_dump -t kns_committee -t kns_jointcommittee -t kns_cmtsitecode -t kns_committeesession -t kns_cmtsessionitem -t kns_documentcommitteesession > /committees_db_dump.sql"
kubectl cp db-87339143-v3mpl:/committees_db_dump.sql ./committees_db_dump.sql
```
