#!/usr/bin/env bash

source bin/k8s_connect.sh

if [ "${1}" == "" ] && [ ! -f ./dump.sql ]; then
    echo "usage: bin/k8s_publish_db_backup.sh <gs_url>"
    echo " > alternatively - create a dump.sql file locally which contains the production db dump"
    exit 1
elif [ "${1}" != "" ]; then
    rm -f ./dump.sql
    echo " > Downloading from ${1}"
    gsutil cp "${1}" ./dump.sql
fi

echo " > Starting a DB container which will be used to sanitize the production DB backup and remove sensitive / unnecessary data"
docker run --name=publish-db-backup -d -e PG_PASSWORD=123456 sameersbn/postgresql:9.6-2

echo " > Sleeping 10 seconds to let DB start"
sleep 10

echo " > Importing the production db dump from ./dump.sql "
docker cp ./dump.sql publish-db-backup:/dump.sql
docker exec -it publish-db-backup bash -c "sudo -u postgres psql -f /dump.sql"

echo " > Exporting a redacted dump to ./redacted.sql"
rm -f ./redacted.sql
docker exec -it publish-db-backup bash -c "sudo -u postgres pg_dump app > /redacted.sql"
docker cp publish-db-backup:/redacted.sql ./redacted.sql

echo " > Copying the redacted sql and publishing it for public access"
gsutil cp ./redacted.sql "gs://kdp-production-db-backups/redacted-`date +%y-%m-%d`.sql"
gsutil acl ch -u AllUsers:R "gs://kdp-production-db-backups/redacted-`date +%y-%m-%d`.sql"

URL="http://storage.googleapis.com/kdp-production-db-backups/redacted-`date +%y-%m-%d`.sql"
echo " > Redacted dump is publically available at ${URL}"

echo " > Building and pushing the image"
docker build -t orihoch/knesset-data-pipelines-bootstrap-db:v0.0.0-`date +%y-%m-%d` devops/db_bootstrap/
docker push orihoch/knesset-data-pipelines-bootstrap-db:v0.0.0-`date +%y-%m-%d`

echo " > Done"
echo
echo " > You can now update the docker compose image to the latest version"
