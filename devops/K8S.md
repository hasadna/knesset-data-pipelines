# Setting knesset-data environment on Kubernetes

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
