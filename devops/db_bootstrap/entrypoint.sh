#!/usr/bin/env bash

if [ -f /redacted.sql ] && [ ! -f "${PG_DATADIR}/db_bootstraped" ]; then
    /sbin/entrypoint.sh &
    touch "${PG_DATADIR}/db_bootstraped"
    sleep 10
    sudo -u postgres psql -f /redacted.sql
    sleep 3
    while true; do
        sleep 86400
    done
else
    exec /sbin/entrypoint.sh
fi
