#!/usr/bin/env bash

gsutil cp gs://knesset-data-pipelines/data/"${1}"/'*' data/"${1}"/
