#!/usr/bin/env bash

while true; do
    # renew daily - certbot will only renew when needed
    echo `date`
    echo "sleeping 86400 seconds until attempting renew"
    sleep 86400
    /renew_certs.sh
done
