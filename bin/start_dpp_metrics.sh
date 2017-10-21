#!/usr/bin/env bash

# start all the celery services - can be used both locally and from within a docker container

while true; do
    sleep "${DPP_METRICS_INTERVAL:-5}"
    if ! dpp_send_metrics; then
        exit 1
    fi
done
