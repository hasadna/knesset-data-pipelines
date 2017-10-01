#!/usr/bin/env bash

source bin/k8s_connect.sh

echo " > generating main release chart devops/k8s/Chart.yaml"
export COMMENT="Helm chart configuration for knesset-data-pipelines project"
if [ -f VERSION.txt ]; then
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi
# Helm linter requires name to be same as parent directory containing the Chart.yaml
export NAME="k8s"
bin/templater.sh devops/k8s/Chart.yaml.template > devops/k8s/Chart.yaml

echo " > generating subcharts"
for chart in devops/k8s/charts/*; do
    chart=`echo $chart | cut -d/ -f4`
    if [ -f "devops/k8s/charts/${chart}/Chart.yaml.template" ]; then
        # Helm linter requires name to be same as parent directory containing the Chart.yaml
        export NAME="${chart}"
        export COMMENT="Helm chart configuration for ${chart}, part of knesset-data-pipelines environment"
        bin/templater.sh "devops/k8s/charts/${chart}/Chart.yaml.template" > "devops/k8s/charts/${chart}/Chart.yaml"
    else
        echo " > WARNING! missing Chart.yaml.template for ${chart} chart"
    fi
done
