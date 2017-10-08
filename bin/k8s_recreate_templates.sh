#!/usr/bin/env bash

# some files are based on .template files which are compiled using this script
# it uses bin/templater.sh to do simple replacing inside the template files
# it's mostly used to apply the current version in chart files

if [ -f VERSION.txt ]; then
    # version is set by external tool - use it directly
    export VERSION=`cat VERSION.txt`
elif which git > /dev/null; then
    # use git to get the version name, add timestamp to ensure version uniqueness (and help debugging)
    export VERSION="`git describe --tags`-`date +%Y-%m-%d-%H-%M`"
else
    # edge-cases where git is not available - version will only include timestamp
    export VERSION="v0.0.0-`date +%Y-%m-%d-%H-%M`"
fi

echo " > VERSION=${VERSION}"


echo " > generating main release chart devops/k8s/Chart.yaml"
export COMMENT="Helm chart configuration for knesset-data-pipelines project"
# Helm linter requires name to be same as parent directory containing the Chart.yaml
# k8s name is not ideal but it works and the name doesn't really matter
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
