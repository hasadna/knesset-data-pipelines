#!/usr/bin/env bash

echo " > service accounts"
gcloud iam service-accounts list

echo " > storage buckets"
gsutil ls

exit 0
