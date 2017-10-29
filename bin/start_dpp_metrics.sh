#!/usr/bin/env bash

# sends metrics which are collected from pipelines api every DPP_METRICS_INTERVAL  (by default = 5 seconds)

while true; do
    sleep "${DPP_METRICS_INTERVAL:-5}"
    if ! dpp_send_metrics; then
        exit 1
    fi
done
