#!/usr/bin/env bash

bin/build.sh
docker tag knesset-data/pipelines orihoch/knesset-data-pipelines
docker push orihoch/knesset-data-pipelines
