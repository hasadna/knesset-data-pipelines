#!/usr/bin/env bash

if [ "${1}" == "" ]; then
    echo "usage: /issue_cert.sh <domain_name>"
else
    echo "issuing certificate for domain ${1}"
    certbot certonly --webroot -w /nginx-html -d $1
fi
